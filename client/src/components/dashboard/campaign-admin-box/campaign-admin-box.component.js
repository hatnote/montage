import './campaign-admin-box.scss';
import template from './campaign-admin-box.html';

const Component = {
  bindings: {
    campaign: '=',
  },
  controller,
  template,
};

function controller() {
  const vm = this;

  vm.link = [
    vm.campaign.id,
    vm.campaign.url_name,
  ].join('-');
}

export default Component;
