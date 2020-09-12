import _ from 'lodash';

import './dashboard.scss';
import template from './archive.tpl.html';

const Component = {
  controller,
  template,
};

function controller(
  $filter,
  $state,
  $mdDialog,
  adminService,
  jurorService,
) {
  const vm = this;

  // functions

  vm.$onInit = () => {
    getAdminData();
    getJurorData();
  };

  function getAdminData() {
    adminService
       .archive()
      .then(data => {
        vm.campaignsAdmin = data.data;
      })
      .catch(err => {
        vm.err = err;
      });
  }

  function getJurorData() {
    jurorService
      .archive()
      .then(data => {
        if (!data.data.length) {
          return;
        }

        const roundsGroupedByCampaigns = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id',
        );
        vm.campaignsJuror = _.values(roundsGroupedByCampaigns);
      })
      .catch(err => {
        vm.err = err;
      });
  }
}

export default Component;
