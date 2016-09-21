import angular from 'angular';
import ngMaterial from 'angular-material';
import uiRouter from 'angular-ui-router';
import sort from './components/angular-sortable-view';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import components from './components';
import services from './services';


angular.module('montage', ['ngMaterial', 'ui.router', 'angular-sortable-view'])
  .config(function ($mdThemingProvider, $provide, $stateProvider, $urlRouterProvider) {
    $mdThemingProvider.generateThemesOnDemand(true);
    $mdThemingProvider.alwaysWatchTheme(true);
    $provide.value('themeProvider', $mdThemingProvider);

    $stateProvider
      .state('main', {
        template: '<ui-view/>',
        resolve: {
          campaigns: (userService) => userService.juror.get()
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
          round: ($stateParams, userService) => userService.juror.getRound($stateParams.id),
          images: (dataService) => dataService.getTempImages() // temporary!
        }
      })
      .state('main.image', {
        url: '/image',
        template: '<mont-image layout="column" layout-align="start start" data="$resolve.image"></mont-round>',
        resolve: {
          image: (dataService) => dataService.getTempImage() // temporary!
        }
      })

      .state('main.admin-dashboard', {
        url: '/admin',
        template: '<mont-dashboard layout="column" layout-align="start start" data="$resolve.campaigns"></mont-dashboard>',
        resolve: {
          campaigns: (userService) => userService.admin.get()
        }
      })
      .state('main.admin-round', {
        url: '/admin/round/:id',
        template: '<mont-round layout="column" layout-align="start start" data="$resolve.round" images="$resolve.images"></mont-round>',
        resolve: {
          round: ($stateParams, userService) => userService.admin.getRound($stateParams.id),
          images: (dataService) => dataService.getTempImages() // temporary!
        }
      })
      .state('main.admin-image', {
        url: '/admin/image',
        template: '<mont-image layout="column" layout-align="start start" data="$resolve.image"></mont-round>',
        resolve: {
          image: (dataService) => dataService.getTempImage() // temporary!
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