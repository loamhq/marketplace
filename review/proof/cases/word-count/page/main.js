import { countWords, label } from './count.js'

// One small label in the composer's tool row. It reads the composer's text
// through the host's own render context, and nothing else.
export function activate(loam) {
  loam.ui.styles.add('page/style.css')
  loam.places.composer.tool.add({
    id: 'word-count.count',
    slot: 'state',
    render: context => {
      const n = countWords(context.text ?? '')
      if (!n) return null
      return loam.ui.h('span', { class: 'word-count', 'aria-live': 'polite', text: label(n) })
    },
  })
}
