import moment from 'moment';

import './campaign.scss';
import templateAdmin from './campaign.tpl.html';
import templateJury from './campaign-jury.tpl.html';

const CampaignComponent = {
    bindings: {
        campaign: '<',
        user: '<',
        type: '<'
    },
    controller: function ($state, $timeout, $mdToast, $templateCache, userService) {
        let vm = this;
        vm.addRound = addRound;
        vm.cancelCampaignName = cancelCampaignName;
        vm.editCampaignName = editCampaignName;
        vm.editRound = editRound;
        vm.nameEdit = '';
        vm.isNameEdited = false;
        vm.openRound = openRound;
        vm.saveCampaignName = saveCampaignName;

        $templateCache.put('campaign-template', isAdmin() ? templateAdmin : templateJury);

        // functions

        function addRound() {
            userService.admin.addRound(vm.campaign.id, {
                round_name: 'Test round',
                quorum: 2,
                jurors: 'Slaporte,MahmoudHashemi'
            }).then((data) => {
                console.log(data);
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

        }

        function isAdmin() {
            return vm.type === 'admin';
        }

        function openRound(round) {
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
