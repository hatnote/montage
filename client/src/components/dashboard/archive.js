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
  jurorService,
) {
  const vm = this;

  vm.isJuror = false;

  // functions

  vm.$onInit = () => {
    getJurorData();
  };

  function getJurorData() {
    jurorService
      .archive()
      .then(data => {
        vm.isJuror = data.data.length;
        vm.user = data.user;
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
