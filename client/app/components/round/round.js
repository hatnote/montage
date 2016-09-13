import _ from 'lodash';

import './round.scss';
import template from './round.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state) {
        let vm = this;
        vm.round = vm.data.data; //vm.data.data.data;
        vm.user = vm.round.user;

        vm.isJuror = isJuror(vm.user.id);
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.size = 1;

        // temp image generator

        vm.images = [];
        for (let i = 0; i < 50; i++) {
            vm.images.push({
                title: 'Image ' + i
            });
        }

        // functions

        function isJuror(id) {
            return !!_.find(vm.round.jurors, {
                active: true,
                id: id
            });
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montRound', RoundComponent);
};
