/**
 * Tiptap HTML → document blocks, for the exporters.
 *
 * Notes are stored as HTML (see `RichEditor.jsx`). Word and PDF cannot render
 * that, and neither can Node, so both exporters need the same small reader:
 * a list of `{ type, text, level }` where `type` is `heading`, `paragraph`,
 * `bullet` or `numbered`.
 *
 * Deliberately a tokeniser, not a parser: it walks the tag stream, tracks the
 * heading level and the list kind, and decodes the entities Tiptap emits. Inline
 * markup (`strong`, `em`, links) is dropped rather than mapped to runs — the
 * exports are printouts of a study note, and a missed `<em>` is a cosmetic
 * difference, while mis-nested runs would be a corrupted paragraph.
 */

const NAMED_ENTITIES = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—',
  ndash: '–', hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“',
  times: '×', divide: '÷', deg: '°', frac12: '½',
}

/** Decode the entities a rich-text editor writes; leave anything else alone. */
export function decodeEntities(text) {
  return text.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, entity) => {
    if (entity.startsWith('#x') || entity.startsWith('#X')) {
      const code = parseInt(entity.slice(2), 16)
      return Number.isFinite(code) ? String.fromCodePoint(code) : match
    }
    if (entity.startsWith('#')) {
      const code = parseInt(entity.slice(1), 10)
      return Number.isFinite(code) ? String.fromCodePoint(code) : match
    }
    const key = entity.toLowerCase()
    return key in NAMED_ENTITIES ? NAMED_ENTITIES[key] : match
  })
}

const HEADING = /^h([1-6])$/i

/** Tag name and closing-ness of one `<…>` token, or null for a non-tag token. */
function tag(token) {
  const m = /^<\s*(\/?)\s*([a-zA-Z][a-zA-Z0-9]*)/.exec(token)
  return m ? { closing: m[1] === '/', name: m[2].toLowerCase() } : null
}

/**
 * HTML → blocks, in document order. Text outside any block element is kept as a
 * paragraph rather than dropped, because a half-written note is still a note.
 */
export function htmlToBlocks(html) {
  const blocks = []
  const listStack = []
  let buffer = ''
  let headingLevel = null

  const flush = () => {
    const text = decodeEntities(buffer).replace(/\s+/g, ' ').trim()
    buffer = ''
    if (!text) return
    const listKind = listStack[listStack.length - 1]
    if (headingLevel) blocks.push({ type: 'heading', level: headingLevel, text })
    else if (listKind === 'ol') blocks.push({ type: 'numbered', text })
    else if (listKind) blocks.push({ type: 'bullet', text })
    else blocks.push({ type: 'paragraph', text })
  }

  for (const token of String(html || '').split(/(<[^>]*>)/)) {
    if (!token) continue
    if (!token.startsWith('<')) {
      buffer += token
      continue
    }
    const t = tag(token)
    if (!t) continue // comment, doctype, or malformed — nothing to render

    if (t.name === 'br') {
      // A soft break inside a paragraph is a space, not a new block.
      buffer += ' '
      continue
    }
    if (t.name === 'ul' || t.name === 'ol') {
      if (!t.closing) listStack.push(t.name)
      else listStack.pop()
      continue
    }
    if (t.name === 'li') {
      if (t.closing) flush()
      else flush() // a stray text node before the <li> still becomes its own block
      continue
    }
    if (HEADING.test(t.name)) {
      if (t.closing) {
        flush()
        headingLevel = null
      } else {
        flush()
        headingLevel = Number(HEADING.exec(t.name)[1])
      }
      continue
    }
    if (t.name === 'p' || t.name === 'div' || t.name === 'blockquote' || t.name === 'pre') {
      flush()
      continue
    }
    // Inline or unknown tags (strong, em, a, span, img, …): keep the text, drop
    // the markup. `img` has no text, so an image is a silent omission — noted in
    // docs/gotchas.md rather than rendered as a broken alt string.
  }
  flush()

  return blocks
}

/** Plain text, for a summary line or a file name. */
export const blocksToText = (blocks) => blocks.map((b) => b.text).join('\n')
