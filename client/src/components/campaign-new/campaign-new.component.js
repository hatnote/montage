import './campaign-new.scss';
import template from './campaign-new.html';

const Component = {
  controller,
  template,
};

function controller(
  $filter,
  $state,
  adminService,
  alertService) {
  const vm = this;

  vm.campaign = {};
  vm.loading = false;

  vm.createCampaign = createCampaign;

  // functions

  vm.$onInit = () => {
    vm.campaign = {
      coordinators: [],
    };
  };

  function createCampaign() {
    const campaign = angular.extend({}, vm.campaign, {
      coordinators: vm.campaign.coordinators.map(user => user.name),
      open_date: $filter('date')(vm.campaign.open_date, 'yyyy-MM-ddTHH:mm:ss'),
      close_date: $filter('date')(vm.campaign.close_date, 'yyyy-MM-ddTHH:mm:ss'),
    });

    vm.loading = true;
    adminService
      .addCampaign(campaign)
      .then((response) => {
        if (response.data.id) {
          $state.go('main.campaign', {
            id: [
              response.data.id,
              response.data.url_name,
            ].join('-'),
          });
        }
      })
      .catch(alertService.error)
      .finally(() => { vm.loading = false; });
  }
}

export default Component;
