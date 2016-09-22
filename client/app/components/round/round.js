import _ from 'lodash';

import './round.scss';
import template from './round.tpl.html';
import imageTemplate from './image.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<',
        user: '=',
        images: '<', // temporary!
        type: '<'
    },
    controller: function ($state, $mdDialog, versionService) {
        let vm = this;
        vm.round = vm.data;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.voting = {
            yesno: vm.round.voteMethod === 'yesno',
            voting: vm.round.voteMethod === 'voting',
            ranking: vm.round.voteMethod === 'ranking',
        };

        vm.isJuror = isJuror(vm.user.id);
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.size = 1;
        vm.openImage = openImage;

        versionService.setVersion(vm.type === 'admin' ? 'grey' : 'blue');

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
                    $scope.isFirst = vm.images.indexOf(image) === 0;
                    $scope.isLast = vm.images.indexOf(image) === vm.images.length - 1;
                    $scope.nextImage = () => {
                        if ($scope.isLast) { return; }
                        const currentIndex = vm.images.indexOf(image);
                        const nextImage = vm.images[currentIndex + 1];
                        $mdDialog.hide();
                        openImage(nextImage);
                    };
                    $scope.prevImage = () => {
                        if ($scope.isFirst) { return; }
                        const currentIndex = vm.images.indexOf(image);
                        const prevImage = vm.images[currentIndex - 1];
                        $mdDialog.hide();
                        openImage(prevImage);
                    };
                    $scope.keyDown = function (event) {
                        if (event.code === 'ArrowRight') {
                            $scope.nextImage();
                        }
                        else if (event.code === 'ArrowLeft') {
                            $scope.prevImage();
                        }
                    };
                }
            }).then(function (answer) {
                // answer
            }, function () {
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
