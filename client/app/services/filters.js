function ordinal() {
    // http://codepen.io/kukicadnan/pen/RNZzjP/
    return (number) => {
        if (isNaN(number) || number < 1) {
            return number;
        } else {
            var lastDigit = number % 10;
            if (lastDigit === 1) {
                return number + 'st';
            } else if (lastDigit === 2) {
                return number + 'nd';
            } else if (lastDigit === 3) {
                return number + 'rd';
            } else if (lastDigit > 3) {
                return number + 'th';
            }
        }
    };
}

export default () => {
    angular
        .module('montage')
        .filter('ordinal', ordinal);
};