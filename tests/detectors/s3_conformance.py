"""S3 — runtime signature / attribute conformance engine (DESIGN §6.3).

Detector for the type of wiring disease CIP documents in `09-bugs-and-issues.md`
(F-13/F-15/F-16/F-17/F-20/F-21/F-31/F-32/F-34/F-35 family): CLI subcommands
parsed but never dispatched, dispatch routed to wrong/arity-mismatched handlers,
`from X import name` of names the target module never defines, module attribute
calls on attributes the module does not export, and `self.<attr>.<missing>`
calls on instance attributes whose class lacks the method.

Pure static analysis (AST + module-level name index). No execution, no
embeddings. Each pass is generic — it fires on any repo whose wiring has the
same failure shape, not on one specific line.

Finding shape mirrors the S5 doctor contract:
{rule, finding_ref, severity, title, evidence, recommendation}
"""

from __future__ import annotations

import ast
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Pass A — module-level name index
# ---------------------------------------------------------------------------

def _top_level_names(tree: ast.Module) -> set[str]:
    """Top-level names a module defines (defs, classes, assigns, imported names).

    Also descends one level into `try`/`if`/`with`/`for` blocks, because a
    module-scope name may be assigned conditionally (e.g. `__version__` inside a
    `try: import importlib.metadata` guard).
    """
    names: set[str] = set()

    def _collect(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Try, ast.If, ast.With, ast.For, ast.While)):
            for child in node.body + (getattr(node, "orelse", []) or []) + (getattr(node, "handlers", []) or []):
                _collect(child)

    for node in tree.body:
        _collect(node)
    return names


def _module_name_index(pkg_root: str) -> dict[str, set[str]]:
    """{module_rel_path: top-level names} over pkg_root/**/*.py (and packages).

    A package dir maps to the union of its `__init__.py` top-level names; if a
    dir has no `__init__.py` it is not a module and is excluded.
    """
    index: dict[str, set[str]] = {}
    for root, _dirs, files in os.walk(pkg_root):
        has_init = "__init__.py" in files
        rel_dir = os.path.relpath(root, pkg_root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        if has_init:
            init_path = os.path.join(root, "__init__.py")
            try:
                tree = ast.parse(Path(init_path).read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                tree = None
            index[rel_dir] = _top_level_names(tree) if tree is not None else set()
        for f in sorted(files):
            if not f.endswith(".py") or f == "__init__.py":
                continue
            path = os.path.join(root, f)
            try:
                tree = ast.parse(Path(path).read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(path, pkg_root).replace("\\", "/")[:-3]
            index[rel] = _top_level_names(tree)
    return index


def _available_modules(pkg_root: str) -> set[str]:
    """All importable rel-paths (module files + packages with __init__)."""
    mods: set[str] = set()
    for root, _dirs, files in os.walk(pkg_root):
        has_init = "__init__.py" in files
        for f in sorted(files):
            if not f.endswith(".py") or f == "__init__.py":
                continue
            rel = os.path.relpath(os.path.join(root, f), pkg_root).replace("\\", "/")[:-3]
            mods.add(rel)
        if has_init:
            rel = os.path.relpath(root, pkg_root).replace("\\", "/")
            if rel == ".":
                rel = ""
            mods.add(rel)
    return mods


def _module_rel_for_bind(
    bind_name: str, pkg_root: str, module_rel: str
) -> str | None:
    """Resolve a local `from . import <bind_name>` to a module rel-path."""
    cand_mod = os.path.join(pkg_root, bind_name + ".py")
    cand_pkg = os.path.join(pkg_root, bind_name)
    if os.path.isfile(cand_mod):
        return bind_name
    if os.path.isdir(cand_pkg) and os.path.isfile(os.path.join(cand_pkg, "__init__.py")):
        return bind_name
    return None


def _collect_module_binds(tree: ast.Module, module_rel: str, pkg_root: str) -> dict[str, str]:
    """module-bound identifiers -> module rel-path, from import statements.

    Only records binds where the identifier refers to a whole module/package
    (`from . import X`, `import cipkg.X`, `from cipkg import X` when X is a
    module) — `from .mod import name` binds go through the Pass-C symbol check,
    not here, so a function-typed name is never mis-read as a module.
    """
    binds: dict[str, str] = {}
    cur_dir = os.path.dirname(module_rel)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "cipkg":
                    continue
                if a.name.startswith("cipkg."):
                    rel = a.name[len("cipkg."):]
                    if rel in _available_modules(pkg_root):
                        binds[a.asname or rel.split(".")[-1]] = rel
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level == 1 and not mod:
                # from . import X   (X is a sibling module/package)
                for a in node.names:
                    if a.name == "*":
                        continue
                    rel = os.path.normpath(os.path.join(cur_dir, a.name)).replace("\\", "/")
                    if rel in _available_modules(pkg_root):
                        binds[a.asname or a.name] = rel
            elif node.level == 1 and mod:
                # from .mod import ...  -> the binding *is* a symbol in .mod
                pass
            elif node.level == 0 and (mod == "cipkg" or mod.startswith("cipkg.")):
                rel = mod[len("cipkg."):] if mod.startswith("cipkg.") else ""
                # `from cipkg import X` binds X only when X is itself a module
                for a in node.names:
                    if a.name == "*":
                        continue
                    cand = os.path.normpath(os.path.join(rel, a.name)).replace("\\", "/")
                    if cand in _available_modules(pkg_root):
                        binds[a.asname or a.name] = cand
    return binds


# ---------------------------------------------------------------------------
# Pass B — CLI wiring
# ---------------------------------------------------------------------------

def _extract_parsed_commands(tree: ast.Module) -> list[str]:
    """Top-level subcommands from `sub.add_parser("<name>")` calls."""
    cmds: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name)
                and fn.value.id == "sub" and fn.attr == "add_parser"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            cmds.append(node.args[0].value)
    return cmds


def _extract_dispatch_entries(tree: ast.Module) -> dict[str, str | None]:
    """handlers dict from dispatch_command: {cmd: handler_name} (None = lambda)."""
    entries: dict[str, str | None] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "handlers" and isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                            continue
                        if isinstance(v, ast.Name):
                            entries[k.value] = v.id
                        else:
                            entries[k.value] = None
    return entries


def _cli_handlers(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    out: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out[node.name] = node
    return out


def _accepts_two_positional(fn: ast.FunctionDef) -> bool:
    """Can dispatch call handler(root, args) without TypeError?

    dispatch_command always calls handler(root, args) — two positionals.
    Only `*args` or >=2 declared positional parameters absorb that safely; a
    single-param handler (e.g. `handle_analyze_command(root)`) raises on every
    dispatch (F-15).
    """
    pos = [a for a in fn.args.posonlyargs + fn.args.args]
    return fn.args.vararg is not None or len(pos) >= 2


# ---------------------------------------------------------------------------
# Pass D — module-attribute call conformance
# ---------------------------------------------------------------------------

def _iter_module_attr_calls(tree: ast.Module):
    """Yield (root_module_name, dotted_chain, lineno) for `module.attr(...)` calls."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        chain: list[str] = []
        cur: ast.expr = fn
        while isinstance(cur, ast.Attribute):
            chain.append(cur.attr)
            cur = cur.value
        if not (isinstance(cur, ast.Name)):
            continue
        chain.reverse()
        if chain:
            yield cur.id, chain, node.lineno


# ---------------------------------------------------------------------------
# Pass E — class-instance attribute conformance (self.<attr>.<member>)
# ---------------------------------------------------------------------------

def _class_instance_attr_calls(tree: ast.Module):
    """Locate `self.<inst>.<member>(...)` calls where <inst> is an own-attrs class.

    `members_by_class[cls]` holds the members each class actually defines; a
    call `self.<inst>.<member>` is checked against the *instance's* class
    (`inst_map[inst]`), never against the class containing the call site.
    """
    classes: dict[str, ast.ClassDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node
    members_by_class: dict[str, set[str]] = {}
    for name, cls in classes.items():
        members: set[str] = set()
        for n in cls.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                members.add(n.name)
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        members.add(t.id)
        members_by_class[name] = members
    for cls_name, cls in classes.items():
        inst_map: dict[str, str] = {}
        for n in ast.walk(cls):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for body_node in ast.walk(n):
                    if not isinstance(body_node, ast.Assign) or len(body_node.targets) != 1:
                        continue
                    t = body_node.targets[0]
                    if not (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                            and t.value.id in ("self", "cls")):
                        continue
                    inst_name = t.attr
                    v = body_node.value
                    if isinstance(v, ast.Call):
                        v = v.func
                    if isinstance(v, ast.Name) and v.id in classes and inst_name not in inst_map:
                        inst_map[inst_name] = v.id
        for n in ast.walk(cls):
            if not isinstance(n, ast.Call):
                continue
            fn = n.func
            if not (isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Attribute)
                    and isinstance(fn.value.value, ast.Name) and fn.value.value.id == "self"):
                continue
            inst, member = fn.value.attr, fn.attr
            target_cls = inst_map.get(inst)
            if target_cls and member not in members_by_class[target_cls]:
                yield cls_name, target_cls, inst, member, n.lineno


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def conformance_checks(pkg_root: str, pkg_name: str = "cipkg") -> list[dict]:
    """Run all S3 passes over pkg_root; return DESIGN §4-shaped findings."""
    findings: list[dict] = []
    index = _module_name_index(pkg_root)
    avail = _available_modules(pkg_root)

    cli_path = os.path.join(pkg_root, "cli.py")
    has_cli = os.path.isfile(cli_path)
    cli_tree = None
    if has_cli:
        try:
            cli_tree = ast.parse(Path(cli_path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            cli_tree = None

    # --- B1: parsed-not-dispatched (F-16) + B2: misrouted (F-17) ---
    if cli_tree is not None:
        parsed = _extract_parsed_commands(cli_tree)
        dispatch = _extract_dispatch_entries(cli_tree)
        handlers = _cli_handlers(cli_tree)
        for cmd in sorted(set(parsed) - set(dispatch)):
            findings.append({
                "rule": "CODE-UNHANDLED-COMMAND",
                "finding_ref": "F-16",
                "severity": "P1",
                "title": f"subcommand '{cmd}' registered but never dispatched",
                "evidence": f"cli.py add_parser('{cmd}') has no entry in dispatch_command handlers",
                "recommendation": "add a handlers dispatch entry (or an explicit not-implemented stub)",
            })
        for cmd, target in sorted(dispatch.items()):
            if target is None:
                continue
            expected = "handle_" + cmd.replace("-", "_") + "_command"
            if target != expected and expected in handlers:
                findings.append({
                    "rule": "CODE-MISROUTED-COMMAND",
                    "finding_ref": "F-17",
                    "severity": "P2",
                    "title": f"'{cmd}' dispatched to {target} instead of {expected}",
                    "evidence": f"cli.py handlers[{cmd!r}] -> {target}; expected handler {expected} exists",
                    "recommendation": "route '{cmd}' to {expected} (missing-dispatch targets are wired)",
                })
        # B3: arity (F-15) — dispatch targets that cannot take (root, args)
        for cmd, target in sorted(dispatch.items()):
            if target is None or target not in handlers:
                continue
            if not _accepts_two_positional(handlers[target]):
                findings.append({
                    "rule": "CODE-ARITY-MISMATCH",
                    "finding_ref": "F-15",
                    "severity": "P2",
                    "title": f"handler {target} cannot accept dispatch's (root, args)",
                    "evidence": f"cli.py def {target}(...{len(handlers[target].args.posonlyargs) + len(handlers[target].args.args)} params) but dispatch calls {target}(root, args)",
                    "recommendation": f"add an `args` parameter to {target} (or gate the call)",
                })

    # --- C: from X import name conformance (F-13/F-34/F-35) ---
    for rel, names in sorted(index.items()):
        if rel == "":
            continue  # the package root itself; call sites live in *.py modules
        path = os.path.join(pkg_root, rel + ".py")
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        cur_dir = "" if "/" not in rel else os.path.dirname(rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            mod = node.module or ""
            level = node.level
            rel_mod = mod.replace(".", "/")
            if level == 1:
                base = os.path.normpath(os.path.join(cur_dir, rel_mod)).replace("\\", "/") if rel_mod else ""
            elif level == 0 and (mod == "cipkg" or mod.startswith("cipkg.")):
                base = rel_mod[len("cipkg"):]
                if base.startswith("/"):
                    base = base[1:]
            else:
                continue
            if level == 1 and not mod:
                # from . import name — name is a sibling module/package or a name
                for a in node.names:
                    if a.name == "*":
                        continue
                    cand = os.path.normpath(os.path.join(cur_dir, a.name)).replace("\\", "/")
                    if cand in avail:
                        continue
                    findings.append({
                        "rule": "CODE-MISSING-MODULE",
                        "finding_ref": "F-13",
                        "severity": "P2",
                        "title": f"import of nonexistent module '{a.name}'",
                        "evidence": f"{rel}.py:{node.lineno}: from . import {a.name}",
                        "recommendation": "import the real module or delete the dead reference",
                    })
                continue
            if base and base not in index:
                src = f"from {mod} import" if level == 0 else f"from .{mod} import"
                findings.append({
                    "rule": "CODE-MISSING-MODULE",
                    "finding_ref": "F-13",
                    "severity": "P2",
                    "title": f"import of nonexistent module '{base}'",
                    "evidence": f"{rel}.py:{node.lineno}: {src} ...",
                    "recommendation": "import the real module (e.g. stack.audit) or delete the dead reference",
                })
                continue
            target_names = index.get(base) or set()
            for a in node.names:
                if a.name == "*":
                    continue
                if a.name in target_names:
                    continue
                # a package may re-export via submodules: base/name[.py|/__init__.py]
                sub = os.path.normpath(os.path.join(base, a.name)).replace("\\", "/") if base else a.name
                if sub in avail:
                    continue
                src = f"from {mod} import" if level == 0 else f"from .{mod} import"
                findings.append({
                    "rule": "CODE-MISSING-SYMBOL",
                    "finding_ref": "F-35",
                    "severity": "P2",
                    "title": f"'{a.name}' not defined in module '{base or pkg_name}'",
                    "evidence": f"{rel}.py:{node.lineno}: {src} {a.name}",
                    "recommendation": "define/export it or import the existing symbol from its real home",
                })

    # --- D: module-attribute call conformance (F-21/F-31/F-32) ---
    for rel, names in sorted(index.items()):
        path = os.path.join(pkg_root, rel + ".py")
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        binds = _collect_module_binds(tree, rel, pkg_root)
        for root_name, chain, lineno in _iter_module_attr_calls(tree):
            tgt_rel = binds.get(root_name)
            if tgt_rel is None or tgt_rel not in index:
                continue
            first = chain[0]
            if first.startswith("_"):
                continue
            tgt_names = index[tgt_rel]
            if first not in tgt_names:
                findings.append({
                    "rule": "CODE-MISSING-SYMBOL",
                    "finding_ref": "F-21",
                    "severity": "P1",
                    "title": f"module '{tgt_rel}' has no attribute '{first}'",
                    "evidence": f"{rel}.py:{lineno}: {root_name}.{'.'.join(chain)}(...)",
                    "recommendation": f"call an attribute '{tgt_rel}' actually exports",
                })

    # --- E: class-instance attribute conformance (F-20) ---
    for rel, names in sorted(index.items()):
        path = os.path.join(pkg_root, rel + ".py")
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for cls, tgt_cls, inst, member, lineno in _class_instance_attr_calls(tree):
            findings.append({
                "rule": "CODE-MISSING-SYMBOL",
                "finding_ref": "F-20",
                "severity": "P1",
                "title": f"{cls}.{inst} instance of '{tgt_cls}' has no member '{member}'",
                "evidence": f"{rel}.py:{lineno}: self.{inst}.{member}(...) ; {tgt_cls} members: {sorted(names)}",
                "recommendation": f"add {member}() to {tgt_cls} or call an existing member",
            })

    return findings