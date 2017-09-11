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

  vm.goTo = goTo;
  vm.goToDashboard = goToDashboard;
  vm.logout = logout;

  // functions

  vm.$onInit = () => {
    userService.getAdmin();
    userService.getJuror();

    userService.getUser()
      .then((data) => { vm.user = data; });
  };

  function goTo(target) {
    vm.loading = true;
    $state.go(target, {}, { reload: true });
  }

  function goToDashboard() {
    const target = $state.current.name.includes('admin') ?
      'main.admin.dashboard' :
      'main.juror.dashboard';
    goTo(target);
  }

  function logout() {
    vm.loading = true;
    userService.logout().then(() => {
      vm.user = {};
      $state.go('main.login');
    });
  }
}

export default Component;
