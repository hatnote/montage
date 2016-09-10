//import './hello.scss';

const HelloComponent = {
  bindings: {
    name: '='
  },
  controller: function() {
    this.greeting = 'Hello';
  },
  template: `<h3 class="header">{{$ctrl.greeting}} dear <strong>{{$ctrl.name}}</strong>!</h3>`
};

export default () => {
  angular
    .module('app')
    .component('hello', HelloComponent);
};
