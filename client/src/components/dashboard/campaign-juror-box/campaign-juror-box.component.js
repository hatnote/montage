import './campaign-juror-box.scss';
import template from './campaign-juror-box.html';

const Component = {
  bindings: {
    rounds: '=',
  },
  controller,
  template,
};

function controller() {
  const vm = this;

  vm.campaign = null;
  vm.collapsed = false;

  vm.collapse = () => { vm.collapsed = !vm.collapsed; };
  vm.isRoundActive = round => round.status === 'active' && round.total_tasks;

  vm.$onInit = () => {
    vm.campaign = vm.rounds.length
      ? vm.rounds[0].campaign
      : null;

    if (vm.rounds.length) {
      const lastRound = vm.rounds[vm.rounds.length - 1];
      vm.collapsed = lastRound.vote_method === 'ranking'
        && lastRound.status === 'finalized';
    }

    vm.voteMethods = {
      yesno: {
        label: 'Yes/No',
        value: 'yesno',
        icon: 'thumbs_up_down',
      },
      rating: {
        label: 'Rating',
        value: 'rating',
        icon: 'star_border',
      },
      ranking: {
        label: 'Ranking',
        value: 'ranking',
        icon: 'sort',
      },
    };
  };
}

export default Component;
