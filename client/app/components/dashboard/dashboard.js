import _ from 'lodash';

import './dashboard.scss';
import template from './dashboard.tpl.html';
import templateNewCampaign from './new-campaign.tpl.html';

const DashboardComponent = {
    bindings: {
        data: '<',
        user: '=',
        type: '<'
    },
    controller: function ($filter, $state, $mdDialog, userService, versionService) {
        let vm = this;
        vm.addCampaign = addCampaign;
        vm.isAdmin = isAdmin;
        vm.isOrganizer = () => vm.user.is_organizer;
        vm.campaigns = isAdmin() ? vm.data.data : _.groupBy(vm.data.data, 'campaign.id');
        vm.logout = logout;
        vm.user = angular.extend(vm.user, vm.data.user);
        vm.error = vm.data.error;


        versionService.setVersion(isAdmin() ? 'grey' : 'blue');

        // functions 

        function addCampaign(event) {
            $mdDialog.show({
                template: templateNewCampaign,
                parent: angular.element(document.body),
                targetEvent: event,
                clickOutsideToClose: false,
                controller: ($scope, $mdDialog, $timeout, dataService) => {
                    $scope.campaign = {
                        name: ''
                        //coordinators: []
                    };
                    $scope.searchUser = (searchName) => dataService.searchUser(capitalize(searchName)).then((response) => {
                        return response.data.query.globalallusers;
                    });
                    $scope.create = function () {
                        let campaign = angular.copy($scope.campaign);
                        /*
                        campaign = angular.extend(campaign, {
                            coordinators: campaign.coordinators.map((element) => element.name).join(',')
                        });
                        */
                        
                        $scope.loading = true;
                        userService.admin.addCampaign(campaign).then((response) => {
                            $scope.loading = false;
                            $mdDialog.hide(true);
                            $state.reload();
                        }, (response) => {
                            $scope.loading = false;
                            console.log('err', response);
                        });
                    };
                    $scope.hide = function () {
                        $mdDialog.hide();
                    };
                    $scope.cancel = function () {
                        $mdDialog.cancel();
                    };
                }
            });
        }

        function capitalize(text) {
            return text.charAt(0).toUpperCase() + text.slice(1);
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
