import { useEffect, useRef } from 'react'
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
  targetLine?: number
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

export default function FileEditor({ text, path, targetLine }: FileEditorProps) {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
  const decorationsRef = useRef<monaco.editor.IEditorDecorationsCollection | null>(null)

  const handleEditorDidMount = (editor: monaco.editor.IStandaloneCodeEditor) => {
    editorRef.current = editor
    if (targetLine && targetLine > 0) {
      editor.revealLineInCenter(targetLine)
      editor.setPosition({ lineNumber: targetLine, column: 1 })
      decorationsRef.current = editor.createDecorationsCollection([
        {
          range: new monaco.Range(targetLine, 1, targetLine, 1),
          options: {
            isWholeLine: true,
            className: 'bg-accent/15 border-l-2 border-accent',
          },
        },
      ])
    }
  }

  useEffect(() => {
    const editor = editorRef.current
    if (!editor) return

    if (targetLine && targetLine > 0) {
      editor.revealLineInCenter(targetLine)
      editor.setPosition({ lineNumber: targetLine, column: 1 })
      if (decorationsRef.current) {
        decorationsRef.current.clear()
      }
      decorationsRef.current = editor.createDecorationsCollection([
        {
          range: new monaco.Range(targetLine, 1, targetLine, 1),
          options: {
            isWholeLine: true,
            className: 'bg-accent/15 border-l-2 border-accent',
          },
        },
      ])
    } else if (decorationsRef.current) {
      decorationsRef.current.clear()
    }
  }, [targetLine, text])

  return (
    <Editor
      height="100%"
      defaultLanguage={inferLanguage(path)}
      theme="vs-dark"
      value={text}
      onMount={handleEditorDidMount}
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