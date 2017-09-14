import _ from 'lodash';

// import './vote.scss';
// import './image.scss';

import template from './vote.html';
import imageTemplate from './image.tpl.html';

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
  $window,
  alertService,
  jurorService) {
  const vm = this;

  let counter = 0;
  let skips = 0;

  vm.encodeName = encodeName;
  vm.error = vm.data.error;
  vm.getImageName = getImageName;
  vm.images = vm.tasks ? vm.tasks.data.tasks : false;
  vm.isVoting = type => vm.round && vm.round.vote_method === type;

  vm.keyDown = keyDown;
  vm.round = vm.data.data;

  vm.openImage = openImage;
  vm.openURL = openURL;
  vm.saveRanking = saveRanking;
  vm.setGallerySize = (size) => { vm.size = size; };
  vm.showSidebar = true;
  vm.size = 1;
  vm.stats = vm.tasks ? vm.tasks.data.stats : false;

  // rating exclusives
  vm.rating = {
    // all: vm.images.length,
    current: vm.images[0],
    currentIndex: 0,
    getNext: getNextImage,
    next: vm.images[1],
    rates: [1, 2, 3, 4, 5],
    setRate,
  };

  // functions

  function encodeName(image) {
    return encodeURI(image.entry.name);
  }

  function getImageName(image) {
    if (!image) return null;

    const entry = image.entry;
    const name = encodeURIComponent(entry.name);
    const url = '//commons.wikimedia.org/w/thumb.php?f=' + name + '&w=';

    if (entry.width <= 800) {
      return url + (entry.width - 1);
    }
    if (entry.width <= 1280) {
      return url + 800;
    }
    return url + 1280;
  }

  function getNextImage() {
    vm.rating.currentIndex = (vm.rating.currentIndex + 1) % vm.images.length;
    vm.rating.current = vm.images[vm.rating.currentIndex];
    vm.rating.next = vm.images[(vm.rating.currentIndex + 1) % vm.images.length];
  }

  function getTasks() {
    return jurorService.getRoundTasks(vm.round.id, skips).then((response) => {
      vm.images = response.data.tasks;
      vm.rating.current = vm.images[0];
      vm.rating.currentIndex = 0;
      vm.rating.next = vm.images[1];
    });
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
      controller: ($scope, $timeout) => {
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

  function saveRanking() {
    vm.loading = true;

    let data = vm.images.map((image) => ({
      task_id: image.id,
      value: vm.images.indexOf(image),
      review: image.review ? image.review : null
    }));

    jurorService.setRating(vm.round.id, {
      ratings: data
    }).then((response) => {
      vm.loading = false;
      response.error ?
        alertService.error(response.error) :
        $state.reload();
    });
  }

  function sendRate(rate) {
    return jurorService.setRating(vm.round.id, {
      ratings: [rate]
    }).then(() => {
      if (vm.stats.total_open_tasks <= 10) {
        skips = 0;
      }
    });
  }

  function setRate(rate) {
    function rating() {
      if (rate) {
        const rating = (rate - 1) / 4;
        vm.loading = true;
        return sendRate({
          'task_id': vm.rating.current.id,
          'value': rating
        }).then(() => {
          vm.loading = false;
          vm.stats.total_open_tasks--;
          return true;
        });
      } else {
        skips++;
        return $q.when(false);
      }
    }

    rating().then(() => {
      if (counter === 4 || !vm.stats.total_open_tasks) {
        counter = 0;
        vm.loading = true;
        getTasks().then(() => {
          vm.loading = false;
        });
      } else {
        counter++;
        vm.rating.getNext();
      }
    });
  }
}

export default Component;
