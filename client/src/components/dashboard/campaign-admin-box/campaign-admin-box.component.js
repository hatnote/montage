import './campaign-admin-box.scss';
import template from './campaign-admin-box.html';

const Component = {
  bindings: {
    campaign: '=',
    index: '<',
  },
  controller,
  template,
};

function controller() {
  const vm = this;

  vm.lastRound = null;
  vm.link = null;

  vm.$onInit = () => {
    if (!vm.campaign) { return; }

    vm.link = [
      vm.campaign.id,
      vm.campaign.url_name,
    ].join('-');

    if (vm.campaign.rounds && vm.campaign.rounds.length) {
      vm.lastRound = {
        number: vm.campaign.rounds.length,
        round: vm.campaign.rounds[vm.campaign.rounds.length - 1],
      };
    }
  };
}

export default Component;
