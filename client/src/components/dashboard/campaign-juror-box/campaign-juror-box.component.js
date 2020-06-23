import './campaign-juror-box.scss';
import template from './campaign-juror-box.html';
import {CAMPAIGN_STATUS_ACTIVE, CAMPAIGN_STATUS_FINALIZED} from "../../../constants";

const Component = {
  bindings: {
    rounds: '=',
  },
  controller,
  template,
};

function controller($state) {
  const vm = this;

  vm.campaign = null;
  vm.collapsed = false;

  vm.collapse = () => { vm.collapsed = !vm.collapsed; };
  vm.goRound = goRound;
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
    if (vm.campaign && vm.campaign.status !== CAMPAIGN_STATUS_ACTIVE) {
      vm.collapsed = true;
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

  function goRound(round, type) {
    if (!vm.isRoundActive(round)) { return; }
    const roundId = [
      round.id,
      round.canonical_url_name,
    ].join('-');
    $state.go(`main.${type || 'vote'}`, { id: roundId });
  }
}

export default Component;
