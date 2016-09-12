import './round.scss';
import template from './round.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state) {
        let vm = this;
        vm.round = vm.data.data.data;
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montRound', RoundComponent);
};
