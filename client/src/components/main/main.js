import template from './main.tpl.html';

const Component = {
  controller,
  template,
};

function controller($state) {
  const vm = this;

  vm.isLinkActive = isLinkActive;

  function isLinkActive(states) {
    const list = angular.isArray(states)
      ? states
      : [states];

    return list.some(stateName => $state.includes(stateName));
  }
}

export default Component;
