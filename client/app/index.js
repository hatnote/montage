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
        template: '<ui-view/>',
        resolve: {
          campaigns: (userService) => userService.getCampaigns()
        }
      })
      .state('main.dashboard', {
        url: '/',
        template: '<mont-dashboard layout="column" layout-align="start start" data="$resolve.campaigns"></mont-dashboard>'
      })
      .state('main.round', {
        url: '/round/:id',
        template: '<mont-round layout="column" layout-align="start start" data="$resolve.round" images="$resolve.images"></mont-round>',
        resolve: {
          round: ($stateParams, userService) => userService.getRound($stateParams.id),
          images: (dataService) => dataService.getTempImages() // temporary!
        }
      })
      .state('login', {
        url: '/login',
        template: '<mont-login layout="column" layout-align="center center"></mont-login>'
      });
    $urlRouterProvider.otherwise('/');
  });

components();
services();