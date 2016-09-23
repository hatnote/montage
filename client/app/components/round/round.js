import './round.scss';
import './image.scss';
import templateMultiple from './round-multiple.tpl.html';
import templateRating from './round-rating.tpl.html';
import imageTemplate from './image.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<',
        user: '=',
        tasks: '<',
        type: '<'
    },
    controller: function ($state, $mdDialog, $templateCache, versionService) {
        let vm = this;
        vm.error = vm.data.error;
        vm.images = vm.tasks.data;
        vm.isVoting = (type) => vm.round.voteMethod === type;
        vm.round = vm.data;
        vm.openImage = openImage;
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.size = 1;
        vm.user = angular.extend(vm.user, vm.data.user);

        versionService.setVersion(vm.type === 'admin' ? 'grey' : 'blue');
        $templateCache.put('round-template', vm.isVoting('rating') ? templateRating : templateMultiple);

        // functions


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
    template: `<ng-include src="'round-template'"/>`
};

export default () => {
    angular
        .module('montage')
        .component('montRound', RoundComponent);
};
