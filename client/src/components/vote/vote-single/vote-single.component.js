import './vote-single.scss';

import template from './vote-single.html';

const Component = {
  bindings: {
    round: '=',
    tasks: '=',
  },
  controller,
  template,
};

function controller(
  $q,
  jurorService) {
  const vm = this;

  let counter = 0;
  let skips = 0;

  vm.encodeName = encodeName;
  vm.getImageName = getImageName;
  vm.images = vm.tasks ? vm.tasks.data.tasks : false;
  vm.isVoting = type => vm.round && vm.round.vote_method === type;

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
    return jurorService
      .getRoundTasks(vm.round.id, skips)
      .then((response) => {
        vm.images = response.data.tasks;
        vm.rating.current = vm.images[0];
        vm.rating.currentIndex = 0;
        vm.rating.next = vm.images[1];
      });
  }

  function sendRate(rate) {
    return jurorService
      .setRating(vm.round.id, { ratings: [rate] })
      .then(() => {
        if (vm.stats.total_open_tasks <= 10) {
          skips = 0;
        }
      });
  }

  function setRate(rate) {
    function rating() {
      if (rate) {
        const value = (rate - 1) / 4;
        vm.loading = true;
        return sendRate({
          task_id: vm.rating.current.id,
          value,
        }).then(() => {
          vm.loading = false;
          vm.stats.total_open_tasks -= 1;
          return true;
        });
      }
      skips += 1;
      return $q.when(false);
    }

    rating().then(() => {
      if (counter === 4 || !vm.stats.total_open_tasks) {
        counter = 0;
        vm.loading = true;
        getTasks().then(() => {
          vm.loading = false;
        });
      } else {
        counter += 1;
        vm.rating.getNext();
      }
    });
  }
}

export default Component;
