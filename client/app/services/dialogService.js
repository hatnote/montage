const DialogService = function ($mdDialog) {

    const service = {
        show: show
    };

    function show(data) {
        $mdDialog.show({
            template: data.template,
            parent: angular.element(document.body),
            targetEvent: event,
            clickOutsideToClose: false,
            controller: ($scope, $mdDialog) => {
                angular.extend($scope, data.scope);
                $scope.cancel = () => $mdDialog.cancel();
                $scope.hide = () => $mdDialog.hide();
                $scope.loading = {};
            }
        });
    }

    return service;
};

export default () => {
    angular
        .module('montage')
        .factory('dialogService', DialogService);
};