import Editor from '@monaco-editor/react'
import { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/editor/editor.worker?worker'
import tsWorker from 'monaco-editor/language/typescript/ts.worker?worker'

// Configures web workers for the bundled monaco-editor (SPEC-06 §7.3: lazy
// Monaco; only JS/TS + editor workers needed for a read-only code viewer).
self.MonacoEnvironment = {
  getWorker(_: unknown, label: string) {
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
  },
}
loader.config({ monaco })

export interface FileEditorProps {
  text: string
  path: string
}

const languageMap: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  py: 'python',
  toml: 'ini',
  md: 'markdown',
  json: 'json',
  css: 'css',
  html: 'html',
  sh: 'shell',
  yml: 'yaml',
  yaml: 'yaml',
}

function inferLanguage(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  return languageMap[ext] ?? 'plaintext'
}

export default function FileEditor({ text, path }: FileEditorProps) {
  return (
    <Editor
      height="100%"
      defaultLanguage={inferLanguage(path)}
      theme="vs-dark"
      value={text}
      options={{
        readOnly: true,
        minimap: { enabled: false },
        fontSize: 13,
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: 'on',
        lineNumbersMinChars: 3,
        renderWhitespace: 'none',
      }}
    />
  )
}