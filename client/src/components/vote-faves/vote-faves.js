import './vote-faves.scss';
import template from './vote-faves.html';

const Component = {
  controller,
  template,
};

function controller(
  $stateParams,
  alertService,
  jurorService) {
  const vm = this;

  vm.loading = false;

  vm.$onInit = () => {
    vm.loading = true;
    jurorService
      .getFaves()
      .then((data) => {
        console.log(data);
      })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  };
}

export default Component;
