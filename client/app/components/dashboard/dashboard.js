import _ from 'lodash';

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
        vm.isAdmin = isAdmin;
        vm.campaigns = isAdmin() ? vm.data.data : _.groupBy(vm.data.data, 'campaign.id');
        vm.logout = logout;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.error = vm.data.error;


        versionService.setVersion(isAdmin() ? 'grey' : 'blue');

        // functions 

        function isAdmin() {
            return vm.type === 'admin';
        }

        function logout() {
            userService.logout().then(() => {
                vm.user = {};
                $state.go('main.login');
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
