export default function ($window) {
  // http://stackoverflow.com/a/17449703/1418878

  const loader = '//upload.wikimedia.org/wikipedia/commons/f/f8/Ajax-loader%282%29.gif';
  return {
    link: (scope, element, attrs) => {
      let img = null;

      const loadImage = () => {
        element[0].src = loader;
        img = new $window.Image();
        img.src = attrs.montSrc;
        img.onload = () => { element[0].src = attrs.montSrc; };
      };

      scope.$watch(() => attrs.montSrc, (newVal, oldVal) => {
        if (oldVal !== newVal) { loadImage(); }
      });
      loadImage();
    },
  };
}
