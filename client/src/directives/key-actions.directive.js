export default function ($window) {
  return {
    scope: {
      actions: '=actions',
    },
    link: (scope, element) => {
      const b = $window.document.getElementsByTagName('body');
      const body = angular.element(b);

      body.on('keydown', (data) => { scope.actions(data); });
      element.on('$destroy', () => { body.off('keydown'); });
    },
  };
}
