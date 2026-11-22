const TEMPLATE = [
  'Please review this pull request diff for:',
  '1. Correctness and edge cases',
  '2. Error handling',
  '3. Missing tests',
  '',
].join('\n')

export function activate(loam) {
  loam.places.composer.tool.add({
    id: 'pr-checklist.template',
    slot: 'state',
    render: context => loam.ui.h('button', {
      type: 'button',
      class: 'pr-checklist-btn',
      'aria-label': 'Insert pull request review checklist',
      onclick: () => {
        try {
          context.insertText?.(TEMPLATE)
        } catch {
          loam.ui.toast?.('Could not insert checklist.')
        }
      },
    }, 'Review PR'),
  })
}
