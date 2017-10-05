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
  $window,
  alertService,
  jurorService) {
  const vm = this;

  let counter = 0;
  let skips = 0;

  vm.images = null;
  vm.rating = {};
  vm.showSidebar = true;
  vm.stats = null;

  vm.encodeName = encodeName;
  vm.keyDown = keyDown;
  vm.getImageName = getImageName;

  // functions

  vm.$onInit = () => {
    if (!vm.tasks || !vm.tasks.data) { return; }

    vm.images = vm.tasks.data.tasks;
    vm.stats = vm.tasks.data.stats;
    vm.rating = {
      // all: vm.images.length,
      current: vm.images[0],
      currentIndex: 0,
      getNext: getNextImage,
      next: vm.images[1],
      rates: [1, 2, 3, 4, 5],
      setRate,
    };
  };

  function encodeName(image) {
    return encodeURI(image.entry.name);
  }

  function getImageName(image) {
    if (!image) return null;

    const entry = image.entry;
    const url = [
      '//commons.wikimedia.org/w/index.php?title=Special:Redirect/file/',
      encodeURIComponent(entry.name),
      '&width=1280',
    ].join('');

    return url;
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

  function keyDown(event) {
    if (vm.round.vote_method === 'yesno') {
      if (event.key === 'ArrowUp') {
        vm.rating.setRate(5);
        alertService.success('Voted: Accept', 250);
      } else if (event.key === 'ArrowDown') {
        vm.rating.setRate(1);
        alertService.success('Voted: Decline', 250);
      }
    } else if (vm.round.vote_method === 'rating') {
      const value = parseInt(event.key, 10);
      if (vm.rating.rates.includes(value)) {
        vm.rating.setRate(value);
        alertService.success(`Voted ${value}/5`, 250);
      }
    }
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
