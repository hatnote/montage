import './toolbar.scss';
import template from './toolbar.html';
import pack from '../../../package.json';

import logo from '../../images/logo_white_fat.svg';

const Component = {
  controller,
  template,
};

function controller($state, $window, userService) {
  const vm = this;

  vm.config = {
    env: $window.__env,
    package: pack,
  };
  vm.logo = logo;
  vm.user = null;

  vm.login = login;
  vm.logout = logout;

  // functions

  vm.$onInit = () => {
    userService.getUser()
      .then((data) => { vm.user = data; });
  };

  function login() {
    vm.loading = true;
    userService.login().then(() => {
      $state.go('main.dashboard', {}, { reload: true });
    });
  }

  function logout() {
    vm.loading = true;
    userService.logout().then(() => {
      vm.user = {};
      $state.go('main.dashboard', {}, { reload: true });
    });
  }
}

export default Component;
