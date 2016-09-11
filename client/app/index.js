import angular from 'angular';
import ngMaterial from 'angular-material';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import components from './components';
import services from './services';

angular.module('app', ['ngMaterial'])
  .config(['$mdThemingProvider', '$provide', function($mdThemingProvider, $provide) {
      $mdThemingProvider.generateThemesOnDemand(true);
      $mdThemingProvider.alwaysWatchTheme(true);
      $provide.value('themeProvider', $mdThemingProvider);
  }]);

const MainComponent = {
  bindings: {},
  controller: function($scope, $mdTheming, dataService, versionService) {
    let vm = this;

    versionService.setVersion('gray');
  },
  template: `<md-toolbar class="md-hue-2">
      <div class="md-toolbar-tools">
        <md-button class="md-icon-button" aria-label="Settings" ng-disabled="true">
          <md-icon>menu</md-icon>
        </md-button>
        <h2>montage</h2>
        <span flex></span>
      </div>
    </md-toolbar>
    <div class="container" layout="row">
      <hello name="'World'"></hello>
    </div>`
};

angular
  .module('montage')
  .component('montMain', MainComponent);

components();
services();
