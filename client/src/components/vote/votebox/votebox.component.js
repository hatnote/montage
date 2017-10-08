import './votebox.scss';
import template from './votebox.html';

const Component = {
  bindings: {
    type: '=',
    voteAction: '=',
  },
  controller,
  template,
};

function controller() {
  const vm = this;

  vm.loading = false;
  vm.setVote = (vote) => {
    vm.loading = true;
    return vm.voteAction(vote)
      .then((data) => {
        vm.loading = false;
        return data;
      });
  };
}

export default Component;
