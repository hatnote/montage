import _ from 'lodash';

import './round.scss';
import './image.scss';
import templateMultiple from './round-multiple.tpl.html';
import templateRating from './round-rating.tpl.html';
import templateYesNo from './round-yesno.tpl.html';
import imageTemplate from './image.tpl.html';

const RoundComponent = {
    bindings: {
        data: '<',
        user: '=',
        tasks: '<',
        type: '<'
    },
    controller: function ($state, $mdDialog, $templateCache, $window, alertService, userService, versionService) {
        let vm = this;
        let getCounter = 0;

        vm.encodeName = encodeName;
        vm.error = vm.data.error;
        vm.getImageName = getImageName;
        vm.images = vm.tasks.data.tasks;
        vm.isVoting = (type) => vm.round && vm.round.vote_method === type;
        vm.keyDown = keyDown;
        vm.round = vm.data.data;
        vm.openImage = openImage;
        vm.openURL = openURL;
        vm.setGallerySize = (size) => { vm.size = size; };
        vm.size = 1;
        vm.stats = vm.tasks.data.stats;
        vm.user = angular.extend(vm.user, vm.data.user);

        // rating exclusives
        vm.rating = {
            all: vm.images.length,
            current: vm.images[0],
            currentIndex: 0,
            getNext: getNextImage,
            next: vm.images[1],
            rates: [1, 2, 3, 4, 5],
            setRate: setRate
        };

        versionService.setVersion(vm.type === 'admin' ? 'admin' : 'juror');
        $templateCache.put('round-template', getTemplate());

        // functions

        function encodeName(image) {
            return encodeURI(image.entry.name);
        }

        function getImageName(image) {
            const entry = image.entry;
            const name = encodeURIComponent(entry.name);
            const url = 'https://commons.wikimedia.org/w/thumb.php?f=' + name + '&w=';

            if (entry.width < 800) {
                return url + (entry.width - 1);
            }
            if (entry.width < 1280) {
                return url + 800;
            }
            return url + 1280;
        }

        function getNextImage(next) {
            if (next) {
                vm.rating.currentIndex = (vm.rating.currentIndex + 1) % vm.rating.all;
            }
            vm.rating.current = vm.images[vm.rating.currentIndex];
            vm.rating.next = vm.images[vm.rating.currentIndex + 1];
        }

        function getTemplate() {
            if (vm.isVoting('rating')) return templateRating;
            if (vm.isVoting('yesno')) return templateYesNo;
            if (vm.isVoting('ranking')) return templateMultiple;
            return '';
        }

        function keyDown(event) {
            const actions = {
                ArrowUp: () => vm.rating.setRate(5),
                ArrowDown: () => vm.rating.setRate(1),
            };

            if (vm.isVoting('yesno') && _.includes(['ArrowUp', 'ArrowDown'], event.key)) {
                actions[event.key]();
            } else if (vm.isVoting('rating') && _.includes(vm.rating.rates, parseInt(event.key))) {
                alertService.success('Rated ' + event.key + '/5', 250);
                vm.rating.setRate(parseInt(event.key));
            }
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

        function setRate(rate) {
            const current = vm.rating.current;
            const rating = (rate - 1) / 4;
            vm.loading = true;

            userService.juror.setRating(vm.round.id, {
                'ratings': [{
                    'task_id': current.id,
                    'value': rating
                }]
            }).then(() => {
                _.pull(vm.images, current);
                getCounter++;
                vm.stats.total_open_tasks--;
                vm.rating.all = vm.images.length;
                vm.rating.getNext();

                if (getCounter === 5) {
                    getCounter = 0;
                    userService.juror.getRoundTasks(vm.round.id).then((response) => {
                        let newImages = response.data.tasks;
                        [].push.apply(vm.images, newImages);
                        vm.images = _.uniqBy(vm.images, 'round_entry_id');
                        vm.loading = false;
                    });
                } else {
                    vm.loading = false;
                }
            });
        }
    },
    template: `<ng-include src="'round-template'"/>`
};

export default () => {
    angular
        .module('montage')
        .component('montRound', RoundComponent)
        .directive('montKeyActions', () => {
            return {
                scope: {
                    actions: '=actions'
                },
                link: (scope, element, attrs) => {
                    const b = document.getElementsByTagName('body');
                    const body = angular.element(b);

                    body.on('keydown', (data) => { scope.actions(data); });
                    element.on('$destroy', () => { body.off('keydown'); });
                }
            };
        });
};