const DialogService = function ($mdDialog) {

    const service = {
        show: show
    };

    function show(data, event) {
        let dialog = {
            template: data.template,
            parent: angular.element(document.body),
            clickOutsideToClose: false,
            controller: ($scope, $mdDialog) => {
                angular.extend($scope, data.scope);
                $scope.cancel = () => $mdDialog.cancel();
                $scope.hide = () => $mdDialog.hide();
                $scope.loading = {};
            }
        };

        if (event) {
            dialog.targetEvent = event;
        }

        $mdDialog.show(dialog);
    }

    return service;
};

export default DialogService;
