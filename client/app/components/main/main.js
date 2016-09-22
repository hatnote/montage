import './main.scss';
import template from './main.tpl.html';

const MainComponent = {
  bindings: {
    user: '='
  },
  controller: function ($state, userService, versionService, $timeout) {
    let vm = this;
    vm.logout = logout;
    vm.showUserMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

    // functions 

    function logout() {
      userService.logout().then(() => {
        vm.user = {};
        $state.go('login');
      });
    }
  },
  template: template
};

export default () => {
  angular
    .module('montage')
    .component('montMain', MainComponent);
};
