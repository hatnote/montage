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
    controller: function ($filter, $mdDialog, $mdToast, $state, $templateCache,
        $timeout, alertService, dataService, dialogService, userService) {
        let vm = this;
        vm.activateRound = activateRound;
        vm.addRound = addRound;
        vm.cancelCampaignName = cancelCampaignName;
        vm.editCampaignName = editCampaignName;
        vm.editRound = editRound;
        vm.isNameEdited = false;
        vm.isLastRoundCompleted = isLastRoundCompleted;
        vm.isRoundActive = isRoundActive;
        vm.nameEdit = '';
        vm.openRound = openRound;
        vm.pauseRound = pauseRound;
        vm.saveCampaignName = saveCampaignName;
        vm.showRoundMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

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
                deadline_date: $filter('date')(round.deadline_date, 'yyyy-MM-ddTHH:mm:ss')
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
                if(response.error) {
                    loading.window = false;
                    alertService.error(response.error);
                    return;
                }

                const id = response.data.id;
                userService.admin.populateRound(id, round_.imports).then((response) => {
                    if(response.error) {
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
                        config: {show_link: true},
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
            let round_ = angular.extend(angular.copy(round), {
                deadline_date: new Date(round.deadline_date)
            });

            dialogService.show({
                template: templateEditRound,
                scope: {
                    round: round_,
                    voteMethods: voteMethods,
                    saveEditRound: saveEditRound,
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

        function pauseRound(round) {
            round.loading = true;
            userService.admin.pauseRound(round.id).then((response) => {
                round.loading = false;
                response.error ?
                    alertService.error(response.error) :
                    $state.reload();
            });
        }

        function saveEditRound(round, loading) {
            loading.window = true;
            userService.admin.editRound(round.id, round).then((response) => {
                if(response.error) {
                    loading.window = false;
                    alertService.error(response.error);
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
        .filter('fromNow', () => (input) => moment(input).fromNow());
};
