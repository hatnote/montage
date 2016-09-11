import angular from 'angular';
import ngMaterial from 'angular-material';
import uiRouter from 'angular-ui-router';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import components from './components';
import services from './services';

angular.module('montage', ['ngMaterial', 'ui.router'])
  .config(function ($mdThemingProvider, $provide, $stateProvider) {
    $mdThemingProvider.generateThemesOnDemand(true);
    $mdThemingProvider.alwaysWatchTheme(true);
    $provide.value('themeProvider', $mdThemingProvider);

    // states
    [
      {
        name: 'hello',
        url: '/hello',
        template: '<hello name="\'Edward\'"></hello>'
      }
    ].forEach(function (state) {
      $stateProvider.state(state);
    });
  });

const MainComponent = {
  bindings: {},
  controller: function ($scope, $mdTheming, dataService, versionService) {
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
        <span>
          <a ui-sref="hello" ui-sref-active="active">Hello</a>
         </span>
      </div>
    </md-toolbar>
    <div class="container" layout="row" flex>
      <ui-view></ui-view>
    </div>`
};

angular
  .module('montage')
  .component('montMain', MainComponent);

components();
services();
