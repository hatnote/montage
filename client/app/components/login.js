const LoginComponent = {
    bindings: {},
    controller: function () {
    },
    template: `<div>
        <md-content>
            Login
        </md-content>
    </div>`
};

export default () => {
    angular
        .module('montage')
        .component('montLogin', LoginComponent);
};
