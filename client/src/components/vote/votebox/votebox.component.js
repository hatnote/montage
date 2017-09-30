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

  vm.setVote = vote => vm.voteAction(vote);
}

export default Component;
