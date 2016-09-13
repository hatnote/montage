import template from './main.tpl.html';

const MainComponent = {
  bindings: {},
  controller: function ($state, userService, versionService) {
    let vm = this;
    userService.getCampaigns().then(data => {
      if (data.data.status === 'failure') {
        $state.go('login');
        return false;
      }
      vm.user = data.data.user;
      console.log(vm);
    });

    versionService.setVersion('blue');
  },
  template: template
};

export default () => {
  angular
    .module('montage')
    .component('montMain', MainComponent);
};
