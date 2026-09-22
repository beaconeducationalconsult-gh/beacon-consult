import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'
import { useEffect } from 'react'

function ToolbarButton({ onClick, active, label, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      aria-pressed={Boolean(active)}
      className={`rounded px-2 py-1 text-xs font-semibold transition-colors ${
        active ? 'bg-brand-600 text-white' : 'text-muted hover:bg-line'
      }`}
    >
      {children}
    </button>
  )
}

/** Outputs HTML — that is what `articles.content` stores. See docs/data-model.md. */
export default function RichEditor({ value = '', onChange, placeholder = 'Write…', limit = 20000 }) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [2, 3] } }),
      Underline,
      Link.configure({ openOnClick: false, autolink: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Placeholder.configure({ placeholder }),
      CharacterCount.configure({ limit }),
    ],
    content: value,
    onUpdate: ({ editor: instance }) => onChange?.(instance.getHTML()),
    editorProps: { attributes: { class: 'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-[16rem] px-4 py-3' } },
  })

  // Keep the editor in step when the parent loads a document after mount.
  useEffect(() => {
    if (!editor) return
    if (value && editor.getHTML() !== value) editor.commands.setContent(value, false)
  }, [value, editor])

  if (!editor) return <div className="card h-64 animate-pulse" />

  const addLink = () => {
    const url = window.prompt('Link URL')
    if (!url) return
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }

  const characters = editor.storage.characterCount.characters()

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-1 border-b border-line-2 bg-surface-2 px-2 py-1.5">
        <ToolbarButton label="Bold" active={editor.isActive('bold')} onClick={() => editor.chain().focus().toggleBold().run()}>
          B
        </ToolbarButton>
        <ToolbarButton label="Italic" active={editor.isActive('italic')} onClick={() => editor.chain().focus().toggleItalic().run()}>
          <em>I</em>
        </ToolbarButton>
        <ToolbarButton label="Underline" active={editor.isActive('underline')} onClick={() => editor.chain().focus().toggleUnderline().run()}>
          <u>U</u>
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-line-2" />
        <ToolbarButton label="Heading 2" active={editor.isActive('heading', { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
          H2
        </ToolbarButton>
        <ToolbarButton label="Heading 3" active={editor.isActive('heading', { level: 3 })} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}>
          H3
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-line-2" />
        <ToolbarButton label="Bullet list" active={editor.isActive('bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()}>
          ••
        </ToolbarButton>
        <ToolbarButton label="Numbered list" active={editor.isActive('orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
          1.
        </ToolbarButton>
        <ToolbarButton label="Quote" active={editor.isActive('blockquote')} onClick={() => editor.chain().focus().toggleBlockquote().run()}>
          ❝
        </ToolbarButton>
        <span className="mx-1 h-4 w-px bg-line-2" />
        <ToolbarButton label="Align left" active={editor.isActive({ textAlign: 'left' })} onClick={() => editor.chain().focus().setTextAlign('left').run()}>
          ⯇
        </ToolbarButton>
        <ToolbarButton label="Align centre" active={editor.isActive({ textAlign: 'center' })} onClick={() => editor.chain().focus().setTextAlign('center').run()}>
          ≡
        </ToolbarButton>
        <ToolbarButton label="Add link" active={editor.isActive('link')} onClick={addLink}>
          🔗
        </ToolbarButton>
        <ToolbarButton label="Undo" onClick={() => editor.chain().focus().undo().run()}>
          ↺
        </ToolbarButton>
        <ToolbarButton label="Redo" onClick={() => editor.chain().focus().redo().run()}>
          ↻
        </ToolbarButton>
      </div>
      <EditorContent editor={editor} />
      <div className="border-t border-line px-4 py-1.5 text-right text-xs text-subtle">
        {characters} / {limit}
      </div>
    </div>
  )
}
