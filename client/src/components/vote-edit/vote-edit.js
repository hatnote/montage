import _ from 'lodash';

import './vote-edit.scss';
import template from './vote-edit.tpl.html';
import imageTemplate from '../vote/image.tpl.html';

const Component = {
  bindings: {
    data: '<',
    tasks: '<',
  },
  controller,
  template,
};

function controller(
  $mdDialog,
  $q,
  $state,
  $templateCache,
  $timeout,
  $window,
  alertService,
  jurorService) {
  const vm = this;

  vm.edits = [];
  vm.sort = {
    order_by: 'date',
    sort: 'desc',
  };

  vm.encodeName = encodeName;
  vm.error = vm.data.error;
  vm.getImageName = getImageName;
  vm.images = vm.tasks.data;
  vm.isVoting = type => vm.round && vm.round.vote_method === type;
  vm.loadMore = loadMore;
  vm.reorderList = reorderList;
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

  vm.$onInit = () => {
    vm.rating = {
      rates: [1, 2, 3, 4, 5],
    };

    vm.images.forEach((element) => {
      element.value = (element.value * 4) + 1;
    });

    vm.round.link = [
      vm.round.id,
      vm.round.canonical_url_name,
    ].join('-');
  };

  // functions

  function encodeName(image) {
    return encodeURI(image.entry.name);
  }

  function getImageName(image) {
    if (!image) { return null; }
    return image.entry.url_med;
  }

  function loadMore() {
    if (vm.loadingMore) return null;

    vm.loadingMore = true;
    return jurorService
      .getPastVotes(vm.round.id, vm.images.length, vm.sort.order_by, vm.sort.sort)
      .then((response) => {
        response.data.forEach((element) => {
          element.value = (element.value * 4) + 1;
        });
        vm.images.push(...response.data);
        if (response.data.length) {
          vm.loadingMore = false;
        }
        return true;
      });
  }

  function openImage(image, event) {
    $mdDialog.show({
      parent: angular.element(document.body),
      targetEvent: event,
      clickOutsideToClose: true,
      template: imageTemplate,
      controller: ($scope) => {
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
        $scope.openURL = openURL;
        $scope.prevImage = () => {
          if ($scope.isFirst) { return; }
          const currentIndex = vm.images.indexOf(image);
          const prevImage = vm.images[currentIndex - 1];
          $mdDialog.hide();
          openImage(prevImage);
        };
        $scope.keyDown = (ev) => {
          if (ev.code === 'ArrowRight') {
            $scope.nextImage();
          } else if (ev.code === 'ArrowLeft') {
            $scope.prevImage();
          }
        };
        $timeout(() => {
          $scope.filePath = '//commons.wikimedia.org/w/thumb.php?f=' + image.entry.name + '&w=800';
        }, 100);
      },
    });
  }

  function openURL(url) {
    $window.open(url, '_blank');
  }

  function reorderList() {
    vm.loading = true;
    vm.loadingMore = false;
    vm.images = [];
    loadMore()
      .then(() => { vm.loading = false; });
  }

  function save() {
    vm.loading = true;
    saveRating()
      .then(() => {
        vm.edits = [];
        vm.images.forEach((image) => { delete image.edited; });
      })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  }

  function saveRating() {
    return jurorService
      .setRating(vm.round.id, {
        ratings: vm.edits.map(element => ({
          vote_id: element.id,
          value: (element.value - 1) / 4,
        })),
      });
  }

  function saveRanking() {
    vm.loading = true;

    const ratings = vm.images.map(image => ({
      task_id: image.task_id,
      value: vm.images.indexOf(image),
      review: image.review ? image.review : null
    }));

    jurorService
      .setRating(vm.round.id, { ratings })
      .then(() => { $state.reload(); })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  }

  function setRate(image, rate) {
    image.value = rate;
    image.edited = true;

    vm.edits = _.reject(vm.edits, { id: image.id });
    vm.edits.push(image);
  }
}

export default Component;
