const AlertService = function ($mdToast) {

    const service = {
        success: (text) => $mdToast.show($mdToast.simple()
            .textContent(text)
            .highlightClass('md-accent')
            .toastClass('toast__top')
            .position('top right')),
        error: (error) => $mdToast.show($mdToast.simple()
            .textContent(error.message + ': ' + error.detail)
            .highlightClass('md-accent')
            .toastClass('toast__top')
            .position('top right'))
    };

    return service;
};

export default () => {
    angular
        .module('montage')
        .factory('alertService', AlertService);
};
