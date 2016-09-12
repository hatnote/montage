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
        name: 'dashboard',
        url: '/dashboard',
        template: '<mont-dashboard layout="column" layout-align="start start" data="$resolve.campaigns"></mont-dashboard>',
        resolve: {
          campaigns: (userService) => userService.getCampaigns()
        }
      },
      {
        name: 'hello',
        url: '/hello',
        template: '<hello name="\'Edward\'"></hello>'
      },
      {
        name: 'login',
        url: '/login',
        template: '<mont-login layout="column" layout-align="center center"></mont-login>'
      }
    ].forEach(function (state) {
      $stateProvider.state(state);
    });
  });

const MainComponent = {
  bindings: {},
  controller: function ($state, dataService, versionService) {
    let vm = this;

    versionService.setVersion('blue');
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
    <div class="container" layout="row" flex>
      <ui-view></ui-view>
    </div>`
};

angular
  .module('montage')
  .component('montMain', MainComponent);

components();
services();