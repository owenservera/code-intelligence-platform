"""Stack-pack self-test: fixture Next.js+Prisma repo with planted defects."""
import os, shutil, tempfile, unittest

SCHEMA = """
model User {
  id    String @id
  email String
  posts Post[]
}

model Post {
  id    String @id
  title String
}
"""
ROUTE = """import { prisma } from "@/lib/db";

export async function GET() {
  const users = await prisma.user.findMany();
  return Response.json(users);
}
"""
CLIENT = """"use client";
import { prisma } from "@prisma/client";

export default function Dashboard() { return null; }
"""
USERS = """import { prisma } from "@/lib/db";

export async function loadUsers(ids: string[]) {
  const out: unknown[] = [];
  for (const id of ids) {
    const u = await prisma.user.findUnique({ where: { id } });
    out.push(u);
  }
  const first = await prisma.user.findFirst({ where: { email: "x@y.z" } });
  return { out, first };
}
"""
CONFIG = """export const stripeKey = "sk_live_abcdefghijklmnop1234";
export const dbUrl = "postgres://admin:hunter22@db.internal/app";
export const flag = process.env.MISSING_VAR;
"""

class StackPack(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-stacktest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        os.makedirs(os.path.join(self.root, "prisma"))
        os.makedirs(os.path.join(self.root, "app", "api", "users"))
        os.makedirs(os.path.join(self.root, "components"))
        os.makedirs(os.path.join(self.root, "lib"))
        w = lambda p, t: open(os.path.join(self.root, p), "w").write(t)
        w("prisma/schema.prisma", SCHEMA)
        w("app/api/users/route.ts", ROUTE)
        w("components/Dashboard.tsx", CLIENT)
        w("lib/users.ts", USERS)
        w("lib/config.ts", CONFIG)
        from .. import indexer
        indexer.sync(self.root, full=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_audit_detects_planted_defects(self):
        from . import audit as sa
        stats = sa.audit(self.root)
        self.assertGreater(stats["open"], 0)
        found = {f["rule"] for f in sa.findings(self.root, limit=500)}
        for expected in ("DB-N1", "NEXT-CLIENT-LEAK", "SEC-HARDCODED-SECRET",
                         "DB-MISSING-INDEX", "NEXT-ROUTE-NO-ERROR",
                         "HIDDEN-MODEL", "ENV-UNDEFINED"):
            self.assertIn(expected, found, f"missing rule output: {expected}")
        self.assertGreaterEqual(stats["critical"], 1)

    def test_quick_wins_and_report(self):
        from . import audit as sa
        sa.audit(self.root)
        self.assertTrue(sa.quick_wins(self.root))
        md = sa.report_markdown(self.root)
        self.assertIn("# CIP Stack Audit", md)

    def test_models_and_routes(self):
        from . import prisma as sp, nextjs as sn
        m = sp.models_report(self.root)
        names = {x["model"]: x for x in m["models"]}
        self.assertIn("User", names); self.assertIn("Post", names)
        self.assertTrue(names["Post"]["orphan"])
        self.assertFalse(names["User"]["orphan"])
        routes = sn.list_routes(self.root)
        self.assertTrue(any(r["path"] == "/api/users" for r in routes))

    def test_impact(self):
        from . import impact as si
        r = si.impact(self.root, target="lib/users.ts")
        self.assertNotIn("error", r)
        self.assertIn("lib/users.ts", r["affected_files"])

def run_stack_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StackPack)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
