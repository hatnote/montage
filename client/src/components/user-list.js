import _ from 'lodash';

const Component = {
  bindings: {
    ngModel: '=',
    ngDisabled: '<',
    max: '<',
  },
  controller,
  template: `<div class="user-list">
    <span class="round__juror" ng-repeat="user in $ctrl.ngModel">
      <span class="juror__avatar" mont-avatar="{{ user.name }}">
        {{ user.name[0].toUpperCase() }}
      </span>
      {{ user.name }}
      <md-icon
          ng-click="$ctrl.removeUser(user)"
          ng-if="!$ctrl.disabled">
        cancel
      </md-icon>
    </span>
    <md-autocomplete flex
      ng-disabled="$ctrl.ngModel.length === $ctrl.maxUsers"
      ng-if="!$ctrl.disabled"
      md-input-name="autocompleteField"
      md-input-minlength="2"
      md-input-maxlength="100"
      md-autoselect="true"
      md-selected-item-change="$ctrl.addUser()"
      md-selected-item="$ctrl.selectedItem"
      md-search-text="$ctrl.searchText"
      md-items="item in $ctrl.searchUser($ctrl.searchText)"
      md-item-text="item.name"
      md-no-cache="true"
      md-floating-label="Enter username"
      md-delay="100">
      <md-item-template>
      <span md-highlight-text="$ctrl.searchText">{{item.name}}</span>
      </md-item-template>
    </md-autocomplete>
  </div>`,
};

function controller(dataService) {
  const vm = this;

  vm.addUser = addUser;
  vm.disabled = vm.ngDisabled;
  vm.maxUsers = vm.max || 999;
  vm.removeUser = user => _.pull(vm.ngModel, user);
  vm.searchText = '';
  vm.searchUser = searchUser;

  // functions 

  function addUser() {
    if (vm.selectedItem) {
      vm.ngModel.push(angular.copy(vm.selectedItem));
    }
    vm.selectedItem = undefined;
  }

  function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function searchUser(searchName) {
    return dataService
      .searchUser(capitalize(searchName))
      .then(data => data.query.globalallusers);
  }
}

export default Component;
