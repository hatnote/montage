import _ from 'lodash';

import './round.scss';
import template from './round.tpl.html';
import imageTemplate from './image.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<',
        images: '<' // temporary!
    },
    controller: function ($state, $mdDialog) {
        let vm = this;
        vm.round = vm.data.data; //vm.data.data.data;
        vm.user = vm.round.user;

        vm.isJuror = isJuror(vm.user.id);
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.size = 1;
        vm.openImage = openImage;

        // functions

        vm.images = vm.images.data.images.map(element => ({
            id: element.id,
            title: element.title,
            name: element.title.replace(/_/gi, ' ')
        })); // temporary!

        function isJuror(id) {
            return !!_.find(vm.round.jurors, {
                active: true,
                id: id
            });
        }

        function openImage(image, event) {
            $mdDialog.show({
                parent: angular.element(document.body),
                targetEvent: event,
                clickOutsideToClose: true,
                template: imageTemplate,
                controller: ($scope, $mdDialog) => {
                    $scope.cancel = () => $mdDialog.hide();
                    $scope.image = image;
                }
            }).then(function(answer) {
                // answer
            }, function() {
                // cancelled
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
