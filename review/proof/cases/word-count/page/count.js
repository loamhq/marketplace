// Counting words, kept apart from the page so it can be tested alone.
// A word is a run of letters, marks, digits or apostrophes in any script.
const WORD = /[\p{L}\p{M}\p{N}'’]+/gu

export function countWords(text) {
  if (typeof text !== 'string' || !text.trim()) return 0
  return (text.match(WORD) ?? []).length
}

export function label(n) {
  return n === 1 ? '1 word' : `${n.toLocaleString()} words`
}
