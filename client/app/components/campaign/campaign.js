import moment from 'moment';

import './campaign.scss';
import templateAdmin from './campaign-admin.tpl.html';
import templateJury from './campaign-jury.tpl.html';
import templateNewRound from './new-round.tpl.html';
import templateEditRound from './edit-round.tpl.html';

const CampaignComponent = {
    bindings: {
        campaign: '<',
        user: '<',
        type: '<'
    },
    controller: function ($filter, $mdDialog, $mdToast, $state, $templateCache, $timeout, alertService, dialogService, userService) {
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

        const voteMethods = [
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


        $templateCache.put('campaign-template', isAdmin() ? templateAdmin : templateJury);

        // functions

        function activateRound(round) {
            userService.admin.activateRound(round.id).then((response) => {
                response.error ?
                    alertService.error(response.error) :
                    $state.reload();
            });
        }

        function createRound(newRound, loading) {
            let round = angular.copy(newRound);
            round = angular.extend(round, {
                jurors: round.jurors.map((element) => element.name),
                deadline_date: $filter('date')(round.deadline_date, 'yyyy-MM-ddTHH:mm:ss')
            });

            loading.window = true;
            userService.admin.addRound(vm.campaign.id, round).then((response) => {
                $mdDialog.hide(true);
                $state.reload();

                response.error ?
                    alertService.error(response.error) :
                    alertService.success('New round added');
            });
        }

        function addRound(event) {
            dialogService.show({
                template: templateNewRound,
                scope: {
                    round: {
                        name: 'Round ' + (vm.campaign.rounds.length + 1),
                        vote_method: 'rating',
                        quorum: 2,
                        jurors: []
                    },
                    createRound: createRound,
                    voteMethods: voteMethods
                }
            });
        }

        function cancelCampaignName() {
            vm.isNameEdited = false;
            vm.nameEdit = '';
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
            dialogService.show({
                template: templateEditRound,
                scope: {
                    round: round,
                    voteMethods: voteMethods
                }
            });
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
            return round.status === 'active' && round.total_tasks;
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
            vm.campaign.name = vm.nameEdit;
            vm.isNameEdited = false;

            userService.admin.editCampaign(vm.campaign.id, {
                name: vm.campaign.name
            }).then((response) => {
                response.error ?
                    alertService.error(response.error) :
                    alertService.success('Campaign name changed');
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
