import './footer.scss';
import template from './footer.html';
import pack from '../../../package.json';

const Component = {
  bindings: {
    user: '=',
  },
  controller,
  template,
};

function controller($window) {
  const vm = this;

  vm.config = {
    env: $window.__env,
    package: pack,
  };
}

export default Component;
