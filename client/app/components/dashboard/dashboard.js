import './dashboard.scss';
import template from './dashboard.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<',
        user: '=',
        type: '<'
    },
    controller: function ($state, userService, versionService) {
        let vm = this;
        vm.campaigns = vm.data.data;
        vm.logout = logout;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.error = vm.data.error;

        versionService.setVersion(vm.type === 'juror' ? 'blue' : 'grey');

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
