import './image.scss';
import template from './image.tpl.html';

const ImageComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state) {
        let vm = this;
        
        vm.image = vm.data;
        vm.rates = [1, 2, 3, 4, 5];
        vm.setRate = (rate) => {
            $state.reload();
        };

        // functions

    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montImage', ImageComponent);
};
