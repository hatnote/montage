var path = require('path');
var webpack = require('webpack');

var config = {
  context: path.join(__dirname, "app"),
  entry: './index.js',
  output: {
    path: path.join(__dirname, "app", "assets"),
    filename: 'bundle.js'
  },
  plugins: [],
  module: {
    loaders: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        loader: 'babel',
        query: {
          presets: ['es2015']
        }
      },
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        loader: 'ng-annotate',
      },
      {
        test: /\.html?$/, loader: 'raw'
      },
      {
        test: /\.css$/, loader: 'style!css'
      },
      {
        test: /\.scss$/, loader: 'style!css!sass'
      },
      {
        test: /\.(png|woff|woff2|eot|ttf|svg)$/, loader: 'url-loader?limit=100000'
      }
    ]
  }
};

if(process.env.NODE_ENV === "production") {
  config.output.path = path.join(__dirname, "dist");
  config.plugins.push(new webpack.optimize.UglifyJsPlugin());
}

module.exports = config;
