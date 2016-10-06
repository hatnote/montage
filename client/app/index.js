import angular from 'angular';
import moment from 'moment';

import 'angular-material';
import 'angular-ui-router';
import './components/angular-sortable-view';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import components from './components';
import services from './services';

angular.module('montage', ['ngMaterial', 'ui.router', 'angular-sortable-view'])
  .config(stateConfig)
  .config(themeConfig)
  .config(localeConfig);

function localeConfig($mdDateLocaleProvider) {
  $mdDateLocaleProvider.firstDayOfWeek = 1;
  $mdDateLocaleProvider.formatDate = function (date) {
    return date ? moment(date).format('YYYY-MM-DD') : '';
  };
  $mdDateLocaleProvider.parseDate = function (dateString) {
    var m = moment(dateString, 'YYYY-MM-DD', true);
    return m.isValid() ? m.toDate() : new Date(NaN);
  };
}

function stateConfig($stateProvider, $urlRouterProvider) {
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
      },
      onEnter: ($state, data) => {
        //invalid cookie userid, try logging in again
        if (data.status === 'failure' && data.errors.length) {
          $state.go('main.login');
        }
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
                      tasks="$resolve.tasks"
                      type="$resolve.userType"></mont-round>`,
      resolve: {
        round: ($stateParams, userService) => userService.juror.getRound($stateParams.id),
        tasks: ($stateParams, userService) => userService.juror.getRoundTasks($stateParams.id)
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
      },
      onEnter: ($state, data) => {
        //invalid cookie userid, try logging in again
        if (data.status === 'failure' && data.errors.length) {
          $state.go('main.login');
        }
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
        round: ($stateParams, userService) => userService.admin.getRound($stateParams.id)
      }
    })
    .state('main.login', {
      url: '/login',
      template: `<mont-login
                      layout="column" layout-align="center center"
                      data="$resolve.data"></mont-login>`,
      resolve: {
        data: (userService) => userService.juror.get()
      },
    });
  $urlRouterProvider.otherwise('/');
}

function themeConfig($mdThemingProvider, $provide) {
  //$mdThemingProvider.generateThemesOnDemand(true);
  $mdThemingProvider.alwaysWatchTheme(true);

  $mdThemingProvider.theme('juror')
    .primaryPalette('blue')
    .accentPalette('red');
  $mdThemingProvider.theme('admin')
    .primaryPalette('blue-grey')
    .accentPalette('red');
  $mdThemingProvider.setDefaultTheme('juror');

  $provide.value('themeProvider', $mdThemingProvider);
}

components();
services();