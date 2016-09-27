import moment from 'moment';

import './campaign.scss';
import templateAdmin from './campaign-admin.tpl.html';
import templateJury from './campaign-jury.tpl.html';
import templateNewRound from './new-round.tpl.html';

const CampaignComponent = {
    bindings: {
        campaign: '<',
        user: '<',
        type: '<'
    },
    controller: function ($filter, $mdDialog, $mdToast, $state, $templateCache, $timeout, userService) {
        let vm = this;
        vm.activateRound = activateRound;
        vm.addRound = addRound;
        vm.cancelCampaignName = cancelCampaignName;
        vm.editCampaignName = editCampaignName;
        vm.editRound = editRound;
        vm.nameEdit = '';
        vm.isNameEdited = false;
        vm.isLastRoundCompleted = isLastRoundCompleted;
        vm.isRoundActive = isRoundActive;
        vm.openRound = openRound;
        vm.saveCampaignName = saveCampaignName;
        vm.showRoundMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

        $templateCache.put('campaign-template', isAdmin() ? templateAdmin : templateJury);

        // functions

        function activateRound(round) {
            userService.admin.activateRound(round.id).then((response) => {
                $state.reload();
            }, (response) => {
                console.log('err', response);
            });
        }

        function addRound(event) {
            $mdDialog.show({
                template: templateNewRound,
                parent: angular.element(document.body),
                targetEvent: event,
                clickOutsideToClose: false,
                controller: ($scope, $mdDialog, $timeout, dataService) => {
                    $scope.round = {
                        name: 'Round ' + (vm.campaign.rounds.length + 1),
                        vote_method: 'rating',
                        quorum: 2,
                        jurors: [],
                        status: 'paused'
                    };
                    $scope.voteMethods = [
                        {
                            label: 'Yes/No',
                            value: 'yesno'
                        },
                        {
                            label: 'Rating',
                            value: 'rating'
                        },
                        {
                            label: 'Ranking',
                            value: 'ranking'
                        }
                    ];
                    $scope.searchUser = (searchName) => dataService.searchUser(capitalize(searchName)).then((response) => {
                        return response.data.query.globalallusers;
                    });

                    $scope.hide = function () {
                        $mdDialog.hide();
                    };
                    $scope.cancel = function () {
                        $mdDialog.cancel();
                    };
                    $scope.create = function () {
                        let round = angular.copy($scope.round);
                        round = angular.extend(round, {
                            jurors: round.jurors.map((element) => element.name).join(','),
                            open_date: $filter('date')(round.open_date, 'yyyy-MM-ddTHH:mm:ss'),
                            close_date: $filter('date')(round.close_date, 'yyyy-MM-ddTHH:mm:ss')
                        });

                        $scope.loading = true;
                        userService.admin.addRound(vm.campaign.id, round).then((response) => {
                            $scope.loading = false;
                            $mdDialog.hide(true);
                            $state.reload();
                        }, (response) => {
                            $scope.loading = false;
                            console.log('err', response);
                        });
                    };
                }
            });
        }

        function cancelCampaignName() {
            vm.isNameEdited = false;
            vm.nameEdit = '';
        }

        function capitalize(text) {
            return text.charAt(0).toUpperCase() + text.slice(1);
        }

        function editCampaignName($event) {
            vm.nameEdit = vm.campaign.name;
            vm.isNameEdited = true;
            $timeout(() => {
                let input = angular.element($event.target).parent().parent().find('input')[0];
                input.focus();
            });
        }

        function editRound(round) {

        }

        function isAdmin() {
            return vm.type === 'admin';
        }

        function isLastRoundCompleted() {
            const rounds = vm.campaign.rounds;
            const isCompleted = rounds.length && rounds[rounds.length - 1].status === 'completed';
            return !rounds.length || isCompleted;
        }

        function isRoundActive(round) {
            return round.status === 'active';
        }

        function openRound(round) {
            if (!isRoundActive(round)) {
                return;
            }

            if (round.voteMethod === 'voting') {
                $state.go('main.juror.image');
            } else {
                $state.go(isAdmin() ? 'main.admin.round' : 'main.juror.round', { id: round.id });
            }
        }

        function saveCampaignName() {
            let toast = $mdToast.simple()
                .textContent('Campaign name changed')
                .action('UNDO')
                .highlightAction(true)
                .highlightClass('md-accent')
                .toastClass('campain__change-name-toast')
                .position('top right');

            vm.campaign.name = vm.nameEdit;
            vm.isNameEdited = false;

            userService.admin.editCampaign(vm.campaign.id, {
                name: vm.campaign.name
            }).then(() => {
                $mdToast.show(toast).then((response) => {
                    console.log(response);
                });
            });
        }
    },
    template: `<ng-include src="'campaign-template'"/>`
};

export default () => {
    angular
        .module('montage')
        .component('montCampaign', CampaignComponent)
        .filter('fromNow', () => (input) => moment(input).fromNow());
};
