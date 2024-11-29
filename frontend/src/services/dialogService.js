import { ref, defineComponent, h, render } from 'vue';
import { CdxDialog } from '@wikimedia/codex';

const dialogService = () => {
  const open = ref(false);
  const dialogConfig = ref({});

  const show = (config) => {
    dialogConfig.value = config;
    open.value = true;
  };

  const DialogComponent = defineComponent({
    setup() {
      const onPrimaryAction = () => {
        open.value = false;
        if (dialogConfig.value.onPrimary) {
          dialogConfig.value.onPrimary();
        }
      };

      const onDefaultAction = () => {
        open.value = false;
        if (dialogConfig.value.onDefault) {
          dialogConfig.value.onDefault();
        }
      };

      return () => h(CdxDialog, {
        open: open.value,
        'onUpdate:open': (value) => open.value = value,
        title: dialogConfig.value.title,
        useCloseButton: true,
        primaryAction: dialogConfig.value.primaryAction,
        defaultAction: dialogConfig.value.defaultAction,
        onPrimary: onPrimaryAction,
        onDefault: onDefaultAction
      }, {
        default: () => h('div', { innerHTML: dialogConfig.value.content })
      });
    }
  });

  const mountDialog = () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    render(h(DialogComponent), container);
  };

  mountDialog();

  return {
    show
  };
};

export default dialogService;