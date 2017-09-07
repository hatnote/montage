const AlertService = function ($mdToast) {

    let toast = $mdToast.simple()
        .highlightClass('md-accent')
        .toastClass('toast__top')
        .position('bottom left');

    const service = {
        success: (text, time) => {
            toast.textContent(text).hideDelay(time || 1000);
            $mdToast.show(toast);
        },
        error: (error, time) => {
            toast.textContent(error.message + ': ' + error.detail).hideDelay(time || 1000);
            $mdToast.show(toast);
        }
    };

    return service;
};

export default () => {
    angular
        .module('montage')
        .factory('alertService', AlertService);
};