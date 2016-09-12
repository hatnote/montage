import angular from 'angular';
import ngMaterial from 'angular-material';
import uiRouter from 'angular-ui-router';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import components from './components';
import services from './services';

angular.module('montage', ['ngMaterial', 'ui.router'])
  .config(function ($mdThemingProvider, $provide, $stateProvider, $urlRouterProvider) {
    $mdThemingProvider.generateThemesOnDemand(true);
    $mdThemingProvider.alwaysWatchTheme(true);
    $provide.value('themeProvider', $mdThemingProvider);

    $stateProvider
      .state('main', {
        abstract: true,
        template: '<ui-view/>',
        resolve: {
          campaigns: function ($state, $timeout, userService) {
            return userService.getCampaigns().then(data => {
              if (data.data.status === 'failure') {
                $timeout(() => $state.go('login'));
                return false;
              } else {
                return data.data.data;
              }
            });
          }
        }
      })
      .state('main.dashboard', {
        url: '/',
        template: '<mont-dashboard layout="column" layout-align="start start" data="$resolve.campaigns"></mont-dashboard>'
      })
      .state('main.round', {
        url: '/round/:id',
        template: '<mont-round layout="column" layout-align="start start" data="$resolve.round"></mont-round>',
        resolve: {
          round: ($stateParams, userService) => userService.getRound($stateParams.id)
        }
      })
      .state('login', {
        url: '/login',
        template: '<mont-login layout="column" layout-align="center center"></mont-login>'
      });
    $urlRouterProvider.otherwise('/');
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
        <h2 ui-sref="main.dashboard">montage</h2>
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