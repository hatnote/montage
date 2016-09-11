import './dashboard.scss';
import template from './dashboard.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state) {
        let vm = this;

        if (vm.data.data.authorized === false) {
            $state.go('login');
            return;
        }

        vm.campaigns = vm.data.data.data;
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montDashboard', DashboardComponent);
};
