import './login.scss';
import template from './login.tpl.html';

import logo from '../../images/logo_blue.svg';

const LoginComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state, $window) {
        var vm = this;
        vm.img = {
            logo: logo
        },
        vm.loading = false;
        vm.login = login;

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

export default LoginComponent;
