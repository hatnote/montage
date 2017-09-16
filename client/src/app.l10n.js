import en from './text/en.json';
import pl from './text/pl.json';

function translateConfig($translateProvider) {
  $translateProvider.translations('en', en);
  $translateProvider.translations('pl', pl);
  $translateProvider.preferredLanguage('en');
  $translateProvider.useSanitizeValueStrategy('escape');
}

export { translateConfig };
