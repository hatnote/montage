import './dashboard.scss';
import template from './dashboard.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state) {
        let vm = this;
        vm.campaigns = vm.data.data.data;
        vm.openRound = openRound;
        
        // functions

        function openRound(id) {
            $state.go('main.round', {id: id});
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montDashboard', DashboardComponent);
};
