import moment from 'moment';

function httpConfig($httpProvider) {
  $httpProvider.interceptors.push('errorService');
}

function localeConfig($mdDateLocaleProvider) {
  $mdDateLocaleProvider.firstDayOfWeek = 1;
  $mdDateLocaleProvider.formatDate = (date) => {
    const d = date ? moment(date).format('YYYY-MM-DD') : '';
    return d;
  };
  $mdDateLocaleProvider.parseDate = (dateString) => {
    const m = moment(dateString, 'YYYY-MM-DD', true);
    return m.isValid() ? m.toDate() : new Date(NaN);
  };
}

function themeConfig($mdThemingProvider, $provide) {
  // $mdThemingProvider.generateThemesOnDemand(true);
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

export { httpConfig, localeConfig, themeConfig };
