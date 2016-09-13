import './login.scss';
import template from './login.tpl.html';

const LoginComponent = {
    bindings: {},
    controller: function ($window) {
        var vm = this;
        vm.loading = false;
        vm.login = login;

        //// functions

        function login() {
            vm.loading = true;
            $window.location.pathname = '/login';
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montLogin', LoginComponent);
};
