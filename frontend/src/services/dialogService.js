import { ref, defineComponent, h, render, getCurrentInstance } from 'vue'
import { CdxDialog } from '@wikimedia/codex'

const dialogService = () => {
  const open = ref(false)
  const dialogConfig = ref({})
  let dialogInstance = null

  const show = (config) => {
    dialogConfig.value = config
    open.value = true
  }

  const DialogComponent = defineComponent({
    setup() {
      const { appContext } = getCurrentInstance()

      const onPrimaryAction = () => {
        open.value = false

        if (dialogInstance?.saveImageData) {
          dialogInstance.saveImageData()
        }

        if (dialogConfig.value.onPrimary) {
          dialogConfig.value.onPrimary()
        }
      }

      const onDefaultAction = () => {
        open.value = false
        if (dialogConfig.value.onDefault) {
          dialogConfig.value.onDefault()
        }
      }

      return () =>
        h(
          CdxDialog,
          {
            appContext: appContext,
            open: open.value,
            'onUpdate:open': (value) => (open.value = value),
            title: dialogConfig.value.title,
            useCloseButton: true,
            primaryAction: dialogConfig.value.primaryAction,
            defaultAction: dialogConfig.value.defaultAction,
            onPrimary: onPrimaryAction,
            onDefault: onDefaultAction,
            style: dialogConfig.value.maxWidth ? { 'max-width': dialogConfig.value.maxWidth } : {}
          },
          {
            default: () => {
              if (typeof dialogConfig.value.content === 'string') {
                return h('div', { innerHTML: dialogConfig.value.content })
              } else if (dialogConfig.value.content) {
                return h(dialogConfig.value.content, {
                  ...dialogConfig.value.props,
                  ref: (el) => (dialogInstance = el)
                })
              }
              return null
            }
          }
        )
    }
  })

  const mountDialog = () => {
    const container = document.createElement('div')
    document.body.appendChild(container)
    render(h(DialogComponent), container)
  }

  mountDialog()

  return {
    show
  }
}

export default dialogService
