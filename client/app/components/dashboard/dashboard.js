import _ from 'lodash';

import './dashboard.scss';
import template from './dashboard.tpl.html';
import templateNewCampaign from './new-campaign.tpl.html';
import templateNewOrganizer from './new-organizer.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<',
        user: '=',
        type: '<'
    },
    controller: function ($filter, $state, $mdDialog, alertService, dialogService, userService, versionService) {
        let vm = this;
        vm.addCampaign = addCampaign;
        vm.addOrganizer = addOrganizer;
        vm.isAdmin = isAdmin;
        vm.isMaintainer = () => vm.user.is_maintainer;
        vm.isOrganizer = () => vm.user.is_organizer;
        vm.campaigns = isAdmin() ? vm.data.data : _.groupBy(vm.data.data, 'campaign.id');
        vm.logout = logout;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.error = vm.data.error;


        versionService.setVersion(isAdmin() ? 'grey' : 'blue');

        // functions 

        function addCampaign(event) {
            dialogService.show({
                template: templateNewCampaign,
                scope: {
                    campaign: {
                        name: '',
                        coordinators: [],
                        open_date: new Date(Date.UTC(2016, 8, 1)),
                        close_date: new Date(Date.UTC(2016, 8, 30))
                    },
                    today: new Date(),
                    create: (campaign_, loading) => {
                        let campaign = angular.copy(campaign_);
                        campaign = angular.extend(campaign, {
                            coordinators: campaign.coordinators.map((element) => element.name),
                            open_date: $filter('date')(campaign.open_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC'),
                            close_date: $filter('date')(campaign.close_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC')
                        });

                        loading.window = true;
                        userService.admin.addCampaign(campaign).then((response) => {
                            if (response.error) {
                                loading.window = false;
                                alertService.error(response.error);
                                return;
                            }

                            loading.window = false;
                            $mdDialog.hide(true);
                            $state.reload();
                        });
                    }
                }
            });
        }

        function addOrganizer(event) {
            dialogService.show({
                template: templateNewOrganizer,
                scope: {
                    organizers: [],
                    add: (data, loading) => {
                        if (!data[0]) {
                            alertService.error({
                                message: 'Error',
                                detail: 'Provide organizer name'
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
                    }
                }
            });
        }

        function isAdmin() {
            return vm.type === 'admin';
        }

        function logout() {
            userService.logout().then(() => {
                vm.user = {};
                $state.go('main.login');
            });
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montDashboard', DashboardComponent);
};
