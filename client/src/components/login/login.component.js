import './login.scss';
import template from './login.html';

const Component = {
  controller,
  template,
};

function controller(
  $state,
  userService) {
  const vm = this;

  vm.loading = false;
  vm.login = login;

  // functions

  function login() {
    vm.loading = true;
    userService.login().then(() => {
      $state.go('main.dashboard', {}, { reload: true });
    });
  }
}

export default Component;
