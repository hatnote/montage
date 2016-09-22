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
        vm.logout = logout;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.error = vm.data.error;

        if (isAdmin()) {
            vm.campaigns = vm.data.data;
        } else {
            vm.campaigns = _.groupBy(vm.data.data, 'campaign_id');
        }

        console.log(vm);

        versionService.setVersion(isAdmin() ? 'grey' : 'blue');

        // functions 

        function isAdmin() {
            return vm.type === 'admin';
        }

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
