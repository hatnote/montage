export default function () {
  // https://stackoverflow.com/a/16348977/1418878

  function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i += 1) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    let color = 0;
    for (let i = 0; i < 3; i += 1) {
      const value = (hash >> (i * 8)) & 0xFF;
      color += value;
    }
    return color;
  }

  function hexToR(h) { return parseInt((cutHex(h)).substring(0, 2), 16); }
  function hexToG(h) { return parseInt((cutHex(h)).substring(2, 4), 16); }
  function hexToB(h) { return parseInt((cutHex(h)).substring(4, 6), 16); }
  function cutHex(h) { return (h.charAt(0) === '#') ? h.substring(1, 7) : h; }

  const colors = [
    '#1abc9c',
    '#2ecc71',
    '#3498db',
    '#9b59b6',
    '#34495e',
    '#16a085',
    '#27ae60',
    '#2980b9',
    '#8e44ad',
    '#2c3e50',
    '#f1c40f',
    '#e67e22',
    '#e74c3c',
    '#95a5a6',
    '#f39c12',
    '#d35400',
    '#c0392b',
    '#bdc3c7',
    '#7f8c8d',
  ];

  return {
    link: (scope, element, attrs) => {
      const sum = stringToColor(attrs.montAvatar);
      const color = colors[sum % 19];
      const rgba = [
        hexToR(color),
        hexToG(color),
        hexToB(color),
        0.5,
      ];
      element[0].style.backgroundColor = `rgba(${rgba.join(',')})`;
    },
  };
}
