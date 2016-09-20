import './campaign.scss';
import template from './campaign.tpl.html';

const CampaignComponent = {
    bindings: {
        data: '<'
    },
    controller: function ($state, $timeout, $mdToast) {
        let vm = this;
        vm.campaign = vm.data;

        vm.cancelCampaignName = cancelCampaignName;
        vm.editCampaignName = editCampaignName;
        vm.editRound = editRound;
        vm.nameEdit = '';
        vm.isNameEdited = false;
        vm.openRound = openRound;
        vm.saveCampaignName = saveCampaignName;

        // functions

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

        function openRound(id) {
            //$state.go('main.round', { id: id });
            $state.go('main.image');
        }

        function saveCampaignName() {
            vm.campaign.name = vm.nameEdit;
            vm.isNameEdited = false;

            let toast = $mdToast.simple()
                .textContent('Campaign name changed')
                .action('UNDO')
                .highlightAction(true)
                .highlightClass('md-accent')
                .toastClass('campain__change-name-toast')
                .position('top right');

            $mdToast.show(toast).then((response) => {
                console.log(response);
            });
        }
    },
    template: template
};

export default () => {
    angular
        .module('montage')
        .component('montCampaign', CampaignComponent);
};
