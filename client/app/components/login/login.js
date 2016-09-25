import './login.scss';
import template from './login.tpl.html';

const LoginComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state, $window, versionService) {
        var vm = this;
        vm.loading = false;
        vm.login = login;

        versionService.setVersion('blue');

        // if ok, move to dashboard
        if(vm.data.status !== 'failure') {
            $state.go('main.juror.dashboard');
        }

        //// functions

        function login() {
            vm.loading = true;
            $window.location.pathname = $window.__env.baseUrl + 'login';
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montLogin', LoginComponent);
};
