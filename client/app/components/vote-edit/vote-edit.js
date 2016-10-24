import _ from 'lodash';

import './vote-edit.scss';
import template from './vote-edit.tpl.html';
import imageTemplate from '../round/image.tpl.html';

const VoteEditComponent = {
    bindings: {
        data: '<',
        user: '=',
        tasks: '<',
        type: '<'
    },
    controller: function ($mdDialog, $q, $state, $templateCache, $window, alertService, userService, versionService) {
        let vm = this;

        let counter = 0;
        let skips = 0;

        vm.edits = [];
        vm.encodeName = encodeName;
        vm.error = vm.data.error;
        vm.getImageName = getImageName;
        vm.images = vm.tasks.data;
        vm.isVoting = (type) => vm.round && vm.round.vote_method === type;
        vm.loadMore = loadMore;
        vm.round = vm.data.data;
        vm.openImage = openImage;
        vm.openURL = openURL;
        vm.save = save;
        vm.saveRanking = saveRanking;
        vm.setRate = setRate;
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.showSidebar = true;
        vm.size = 1;
        vm.stats = vm.tasks.data.stats;
        vm.user = angular.extend(vm.user, vm.data.user);

        // rating exclusives
        vm.rating = {
            rates: [1, 2, 3, 4, 5],
        };

        versionService.setVersion('juror');
        $templateCache.put('round-template', getTemplate());

        vm.images.forEach((element) => {
            element.value = element.value * 4 + 1;
        });

        // functions

        function encodeName(image) {
            return encodeURI(image.entry.name);
        }

        function getImageName(image) {
            if (!image) return;
            return image.entry.url_med;
        }

        function getTasks() {
            return userService.juror.getRoundTasks(vm.round.id, skips).then((response) => {
                vm.images = response.data.tasks;
                vm.rating.current = vm.images[0];
                vm.rating.currentIndex = 0;
                vm.rating.next = vm.images[1];
            });
        }

        function getTemplate() {
            return template;
        }

        function loadMore() {
            if (vm.loadingMore) return;

            vm.loadingMore = true;
            userService.juror.getPastVotes(vm.round.id, vm.images.length).then((response) => {
                response.data.forEach((element) => {
                    element.value = element.value * 4 + 1;
                });
                vm.images.push.apply(vm.images, response.data);
                if (response.data.length) {
                    vm.loadingMore = false;
                }
            });
        }

        function openImage(image, event) {
            $mdDialog.show({
                parent: angular.element(document.body),
                targetEvent: event,
                clickOutsideToClose: true,
                template: imageTemplate,
                controller: ($scope, $mdDialog, $timeout) => {
                    $scope.cancel = () => $mdDialog.hide();
                    $scope.image = image;
                    $scope.isFirst = vm.images.indexOf(image) === 0;
                    $scope.isLast = vm.images.indexOf(image) === vm.images.length - 1;
                    $scope.isRanking = vm.isVoting('ranking');
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
                    $timeout(() => {
                        $scope.filePath = 'https://commons.wikimedia.org/w/thumb.php?f=' + image.entry.name + '&w=800';
                    }, 100);
                }
            }).then(function (answer) {
                // answer
            }, function () {
                // cancelled
            });
        }

        function openURL(url) {
            $window.open(url, '_blank');
        }

        function save() {
            vm.loading = true;
            saveRating().then((response) => {
                vm.edits = [];
                vm.images.forEach((image) => { delete image.edited; });
                vm.loading = false;
                response.error ?
                    alertService.error(response.error) :
                    alertService.success('New votes saved');
            });
        }

        function saveRating() {
            return userService.juror.setRating(vm.round.id, {
                ratings: vm.edits.map((element) => ({
                    task_id: element.task_id,
                    value: (element.value - 1) / 4
                }))
            });
        }

        function saveRanking() {
            vm.loading = true;

            let data = vm.images.map((image) => ({
                task_id: image.task_id,
                value: vm.images.indexOf(image),
                review: image.review ? image.review : null
            }));

            userService.juror.setRating(vm.round.id, {
                ratings: data
            }).then((response) => {
                vm.loading = false;
                response.error ?
                    alertService.error(response.error) :
                    $state.reload();
            });
        }

        function setRate(image, rate) {
            image.value = rate;
            image.edited = true;

            vm.edits = _.reject(vm.edits, { id: image.id });
            vm.edits.push(image);
        }
    },
    template: `<ng-include src="'round-template'"/>`
};

export default () => {
    angular
        .module('montage')
        .component('montVoteEdit', VoteEditComponent);
};
