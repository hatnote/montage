import moment from 'moment';

import './campaign.scss';
import templateAdmin from './campaign-admin.tpl.html';
import templateJury from './campaign-jury.tpl.html';
import templateNewRound from './new-round.tpl.html';
import templateEditCampaign from './edit-campaign.tpl.html';
import templateEditRound from './edit-round.tpl.html';

const CampaignComponent = {
    bindings: {
        campaign: '<',
        user: '<',
        type: '<'
    },
    controller: function ($filter, $mdDialog, $mdToast, $q, $state, $templateCache,
        $timeout, alertService, dataService, dialogService, userService) {
        let vm = this;
        vm.activateRound = activateRound;
        vm.addRound = addRound;
        vm.cancelCampaignName = cancelCampaignName;
        vm.editCampaign = editCampaign;
        vm.editCampaignName = editCampaignName;
        vm.editRound = editRound;
        vm.isNameEdited = false;
        vm.isLastRoundCompleted = isLastRoundCompleted;
        vm.isRoundActive = isRoundActive;
        vm.loadRoundDetails = loadRoundDetails;
        vm.nameEdit = '';
        vm.openRound = openRound;
        vm.pauseRound = pauseRound;
        vm.roundDetails = {};
        vm.saveCampaignName = saveCampaignName;
        vm.showRoundMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

        //vm.campaign.rounds = vm.campaign.rounds.filter((round) => round.status !== 'cancelled');

        const voteMethods = {
            'yesno': {
                label: 'Yes/No',
                value: 'yesno',
                icon: 'thumbs_up_down'
            },
            'rating': {
                label: 'Rating',
                value: 'rating',
                icon: 'star_border'
            }
            /*
            'ranking': {
                label: 'Ranking',
                value: 'ranking',
                icon: 'sort'
            }
            */
        };


        $templateCache.put('campaign-template', isAdmin() ? templateAdmin : templateJury);

        // functions

        function activateRound(round) {
            round.loading = true;
            userService.admin.activateRound(round.id).then((response) => {
                round.loading = false;
                response.error ?
                    alertService.error(response.error) :
                    $state.reload();
            });
        }

        function createRound(round, loading) {
            let round_ = angular.copy(round);
            round_ = angular.extend(round_, {
                jurors: round.jurors.map((element) => element.name),
                deadline_date: $filter('date')(round.deadline_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC')
            });

            if (!round_.name) {
                alertService.error({
                    message: 'Error',
                    detail: 'Name cannot be empty'
                });
                return;
            }
            if (!round_.deadline_date) {
                alertService.error({
                    message: 'Error',
                    detail: 'Deadline date cannot be empty'
                });
                return;
            }
            if (!round_.jurors.length) {
                alertService.error({
                    message: 'Error',
                    detail: 'Jurors must be added'
                });
                return;
            }
            if (!round_.quorum) {
                alertService.error({
                    message: 'Error',
                    detail: 'Quorum value is empty on invalid'
                });
                return;
            }

            loading.window = true;
            userService.admin.addRound(vm.campaign.id, round_).then((response) => {
                if (response.error) {
                    loading.window = false;
                    alertService.error(response.error);
                    return;
                }

                const id = response.data.id;
                userService.admin.populateRound(id, round_.imports).then((response) => {
                    if (response.error) {
                        loading.window = false;
                        alertService.error(response.error);
                        return;
                    }

                    alertService.success('New round added');
                    $mdDialog.hide(true);
                    $state.reload();
                });
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
                        jurors: [],
                        config: { show_link: true },
                        imports: {
                            import_method: 'category',
                            category: ''
                        }
                    },
                    createRound: createRound,
                    searchCategory: (name) => dataService.searchCategory(name).then((response) => {
                        return response.data[1].map((element) => element.substring(9));
                    }),
                    voteMethods: voteMethods,
                    today: new Date()
                }
            }, event);
        }

        function cancelCampaignName() {
            vm.isNameEdited = false;
            vm.nameEdit = '';
        }

        function editCampaign(event) {
            let campaign = angular.extend(angular.copy(vm.campaign), {
                open_date: new Date(vm.campaign.open_date),
                close_date: new Date(vm.campaign.close_date),
                coordinators: vm.campaign.coordinators.map((user) => ({ name: user.username }))
            });

            dialogService.show({
                template: templateEditCampaign,
                scope: {
                    campaign: campaign,
                    saveEditCampaign: saveEditCampaign,
                }
            }, event);
        }

        function editCampaignName($event) {
            vm.nameEdit = vm.campaign.name;
            vm.isNameEdited = true;
            $timeout(() => {
                let input = angular.element($event.target).parent().parent().find('input')[0];
                input.focus();
            });
        }

        function editRound(round, event) {
            let round_ = angular.extend(angular.copy(round), {
                deadline_date: new Date(round.deadline_date),
                jurors: round.jurors.map((user) => ({ name: user.username }))
            });

            dialogService.show({
                template: templateEditRound,
                scope: {
                    round: round_,
                    voteMethods: voteMethods,
                    saveEditRound: saveEditRound,
                }
            }, event);
        }

        function isAdmin() {
            return vm.type === 'admin';
        }

        function isLastRoundCompleted() {
            const rounds = vm.campaign.rounds;
            const isCompleted = rounds.length && (rounds[rounds.length - 1].status === 'completed' || rounds[rounds.length - 1].status === 'cancelled');
            return !rounds.length || isCompleted;
        }

        function isRoundActive(round) {
            return round.status === 'active' && round.total_tasks;
        }

        function loadRoundDetails(round) {
            const id = round.id;
            vm.roundDetails[id] = 'loading';
            userService.admin.getRound(id).then((response) => {
                vm.roundDetails[id] = response.data;
            });
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

        function pauseRound(round) {
            round.loading = true;
            userService.admin.pauseRound(round.id).then((response) => {
                round.loading = false;
                response.error ?
                    alertService.error(response.error) :
                    $state.reload();
            });
        }

        function saveEditCampaign(campaign, loading) {
            loading.window = true;

            let campaign_ = angular.extend(angular.copy(campaign), {
                coordinators: campaign.coordinators.map((element) => element.name),
                open_date: $filter('date')(campaign.open_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC'),
                close_date: $filter('date')(campaign.close_date, 'yyyy-MM-ddTHH:mm:ss', 'UTC')
            });

            userService.admin.editCampaign(campaign_.id, campaign_).then((response) => {
                if (response.error) {
                    loading.window = false;
                    alertService.error(response.error);
                    return;
                }

                alertService.success('Campaign settings saved');
                $mdDialog.hide(true);
                $state.reload();
            });
        }

        function saveEditRound(round, loading) {
            loading.window = true;

            const jurors = round.jurors.map((user) => user.name);
            $q.all({
                round: userService.admin.editRound(round.id, round),
                jurors: userService.admin.editJurors(round.id, { new_jurors: jurors })
            }).then((response) => {
                if (response.round.error) {
                    loading.window = false;
                    alertService.error(response.round.error);
                    return;
                }

                alertService.success('Round settings saved');
                $mdDialog.hide(true);
                $state.reload();
            });
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
        .filter('fromNow', () => (input) => moment.utc(input).fromNow());
};
