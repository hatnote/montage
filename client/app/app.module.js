import angular from 'angular';
import moment from 'moment';

import 'angular-material';
import 'angular-ui-router';
import 'ng-infinite-scroll';
import './components/angular-sortable-view';

import './style.scss';
import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';

import stateConfig from './app.routing';

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


export default () => {
    angular.module('montage', [
        'ngMaterial',
        'ui.router',
        'angular-sortable-view',
        'infinite-scroll'
    ])
        .config(stateConfig)
        .config(themeConfig)
        .config(localeConfig);
};