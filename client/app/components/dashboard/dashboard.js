import './dashboard.scss';
import template from './dashboard.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state, userService) {
        let vm = this;
        vm.campaigns = vm.data.data;
        vm.logout = logout;
        vm.user = vm.data.user;
        vm.error = vm.data.error;

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
        .component('montDashboard', DashboardComponent);
};
