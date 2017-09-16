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
  const tp = $mdThemingProvider;
  tp.definePalette('belize', tp.extendPalette('blue', {
    500: '#36c',
    600: '#36c',
  }));
  tp.theme('default')
    .primaryPalette('belize')
    .accentPalette('grey');

  $provide.value('themeProvider', tp);
}

export { httpConfig, localeConfig, themeConfig };
