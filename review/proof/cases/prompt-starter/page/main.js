const BUTTON_LABEL = 'AI assistant'
const STARTER = 'Help me outline the next three steps for: '

export function activate(loam) {
  loam.places.composer.tool.add({
    id: 'prompt-starter.btn',
    slot: 'state',
    render: context => loam.ui.h('button', {
      type: 'button',
      class: 'prompt-starter-btn',
      'aria-label': BUTTON_LABEL,
      onclick: () => {
        try {
          context.insertText?.(STARTER)
        } catch {
          loam.ui.toast?.('Could not insert starter text.')
        }
      },
    }, BUTTON_LABEL),
  })
}
