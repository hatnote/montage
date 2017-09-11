import _ from 'lodash';

import './dashboard.scss';
import template from './dashboard.tpl.html';
import templateNewCampaign from './new-campaign.tpl.html';
import templateNewOrganizer from './new-organizer.tpl.html';

const Component = {
  controller,
  template,
};

function controller(
  $filter,
  $state,
  $mdDialog,
  adminService,
  alertService,
  dialogService,
  userService) {
  const vm = this;

  vm.isAdmin = false;
  vm.isJuror = false;
  vm.campaigns = [];

  vm.addCampaign = addCampaign;
  vm.addOrganizer = addOrganizer;

/*   if (!vm.data.error) {
    vm.campaigns = isAdmin() ?
      vm.data.data :
      _.groupBy(vm.data.data.filter((round) => round.status !== 'cancelled'), 'campaign.id');
  } */

  // functions 

  vm.$onInit = () => {
    getAdminData();
    getJurorData();
  };

  function getAdminData() {
    userService.getAdmin()
      .then((data) => {
        vm.isAdmin = data.data.length;
        vm.campaignsAdmin = data.data;
      });
  }

  function getJurorData() {
    userService.getJuror()
      .then((data) => {
        vm.isJuror = data.data.length;
        vm.user = data.user;
        if (!data.data.length) { return; }

        const grupped = _.groupBy(
          data.data.filter(round => round.status !== 'cancelled'),
          'campaign.id');
        vm.campaignsJuror = _.values(grupped);
      });
  }

  function addCampaign() {
    dialogService.show({
      template: templateNewCampaign,
      scope: {
        campaign: {
          name: '',
          coordinators: [],
          open_date: new Date(Date.UTC(2017, 8, 1)),
          close_date: new Date(Date.UTC(2017, 8, 30)),
        },
        today: new Date(),
        create: (campaign_, loading) => {
          let campaign = angular.copy(campaign_);
          campaign = angular.extend(campaign, {
            coordinators: campaign.coordinators.map(element => element.name),
            open_date: $filter('date')(campaign.open_date, 'yyyy-MM-ddTHH:mm:ss'),
            close_date: $filter('date')(campaign.close_date, 'yyyy-MM-ddTHH:mm:ss'),
            url: 'https://commons.wikimedia.org/',
          });

          loading.window = true;
          adminService.addCampaign(campaign).then((response) => {
            if (response.error) {
              loading.window = false;
              alertService.error(response.error);
              return;
            }

            loading.window = false;
            $mdDialog.hide(true);
            $state.reload();
          });
        },
      },
    });
  }

  function addOrganizer() {
    dialogService.show({
      template: templateNewOrganizer,
      scope: {
        organizers: [],
        add: (data, loading) => {
          if (!data[0]) {
            alertService.error({
              message: 'Error',
              detail: 'Provide organizer name',
            });
            return;
          }

          loading.window = true;
          const userName = data[0].name;
          userService.admin.addOrganizer({ username: userName }).then((response) => {
            if (response.error) {
              loading.window = false;
              alertService.error(response.error);
              return;
            }

            alertService.success(userName + ' added as an organizer');
            $mdDialog.hide(true);
            $state.reload();
          });
        },
      },
    });
  }
}

export default Component;
