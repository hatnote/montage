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
        template: '<mont-main user="$resolve.user"></mont-main>',
        resolve: {
          user: ($q) => $q.when({})
        }
      })

      .state('main.juror', {
        template: '<ui-view/>',
        resolve: {
          data: (userService) => userService.juror.get(),
          userType: ($q) => $q.when('juror')
        }
      })
      .state('main.juror.dashboard', {
        url: '/',
        template: `<mont-dashboard
                      layout="column" layout-align="start start"
                      data="$resolve.data"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-dashboard>`
      })
      .state('main.juror.round', {
        url: '/round/:id',
        template: `<mont-round
                      layout="column" layout-align="start start"
                      data="$resolve.round"
                      user="$resolve.user"
                      images="$resolve.images"
                      type="$resolve.userType"></mont-round>`,
        resolve: {
          round: ($stateParams, userService) => userService.juror.getRound($stateParams.id),
          images: (dataService) => dataService.getTempImages() // temporary!
        }
      })
      .state('main.juror.image', {
        url: '/image',
        template: `<mont-image
                      layout="column" layout-align="start start"
                      data="$resolve.image"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-round>`,
        resolve: {
          image: (dataService) => dataService.getTempImage() // temporary!
        }
      })

      .state('main.admin', {
        template: '<ui-view/>',
        resolve: {
          data: (userService) => userService.admin.get(),
          userType: ($q) => $q.when('admin')
        }
      })
      .state('main.admin.dashboard', {
        url: '/admin',
        template: `<mont-dashboard
                      layout="column" layout-align="start start"
                      data="$resolve.data"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-dashboard>`
      })
      .state('main.admin.round', {
        url: '/admin/round/:id',
        template: `<mont-round
                      layout="column" layout-align="start start"
                      data="$resolve.round"
                      user="$resolve.user"
                      images="$resolve.images"
                      type="$resolve.userType"></mont-round>`,
        resolve: {
          round: ($stateParams, userService) => userService.admin.getRound($stateParams.id),
          images: (dataService) => dataService.getTempImages() // temporary!
        }
      })
      .state('main.admin.image', {
        url: '/admin/image',
        template: `<mont-image
                      layout="column" layout-align="start start"
                      data="$resolve.image"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-round>`,
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