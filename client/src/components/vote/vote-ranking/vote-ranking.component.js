import './vote-ranking.scss';
import template from './vote-ranking.html';
import imageTemplate from '../image.tpl.html';

const Component = {
  bindings: {
    round: '=',
    tasks: '=',
  },
  controller,
  template,
};

function controller(
  $mdDialog,
  $state,
  $window,
  alertService,
  jurorService) {
  const vm = this;

  vm.images = null;

  vm.editPreviousVotes = editPreviousVotes;
  vm.openImage = openImage;
  vm.saveRanking = saveRanking;
  vm.setGallerySize = (size) => { vm.size = size; };

  // functions

  vm.$onInit = () => {
    if (!vm.tasks || !vm.tasks.data) { return; }

    vm.round.link = [
      vm.round.id,
      vm.round.canonical_url_name,
    ].join('-');

    vm.images = vm.tasks.data.tasks;
    vm.stats = vm.tasks.data.stats;
  };

  /**
   * 
   */
  function editPreviousVotes() {
    vm.loading = true;
    $state.go('main.vote-edit', { id: vm.round.link });
  }

  /**
   * 
   * @param {*} image 
   * @param {*} event 
   */
  function openImage(image, event) {
    $mdDialog.show({
      parent: angular.element($window.document.body),
      targetEvent: event,
      clickOutsideToClose: true,
      template: imageTemplate,
      controller: ($scope, $timeout) => {
        $scope.cancel = () => $mdDialog.hide();
        $scope.image = image;
        $scope.isFirst = vm.images.indexOf(image) === 0;
        $scope.isLast = vm.images.indexOf(image) === vm.images.length - 1;
        $scope.isRanking = true;
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
        $scope.keyDown = (ev) => {
          if (ev.code === 'ArrowRight') {
            $scope.nextImage();
          } else if (ev.code === 'ArrowLeft') {
            $scope.prevImage();
          }
        };
        $timeout(() => {
          $scope.filePath = [
            '//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/',
            encodeURIComponent(image.entry.name),
            '&width=800',
          ].join('');
        }, 100);
      },
    });
  }

  /**
   * 
   */
  function saveRanking() {
    vm.loading = true;

    const ratings = vm.images.map(image => ({
      task_id: image.id,
      value: vm.images.indexOf(image),
      review: image.review ? image.review : null,
    }));

    jurorService
      .setRating(vm.round.id, { ratings })
      .then(() => { $state.reload(); })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  }
}

export default Component;
