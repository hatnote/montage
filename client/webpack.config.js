var path = require('path');
var webpack = require('webpack');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var ngAnnotatePlugin = require('ng-annotate-webpack-plugin');

var config = {
  context: path.join(__dirname, 'app'),
  entry: './index.js',
  output: {
    path: path.join(__dirname, '..', 'montage', 'static', 'assets'),
    filename: 'bundle.js'
  },
  plugins: [new HtmlWebpackPlugin({
    template: 'index_local.ejs',
    filename: path.join('..', 'index.html')
  })],
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

var ENV = process.env.NODE_ENV;
if (ENV === 'prod' || ENV === 'dev') {
  config.output = {
    path: path.join(__dirname, '..', 'montage', 'static', 'dist'),
    filename: 'bundle.min.js'
  };
  config.plugins = [
    new HtmlWebpackPlugin({
      template: ENV === 'dev' ? 'index_dev.ejs' : 'index_prod.ejs',
      filename: path.join('..', 'index.html')
    }),
    new ngAnnotatePlugin({
      add: true
    }),
    new webpack.optimize.UglifyJsPlugin({
      compress: {
        warnings: false
      },
      mangle: false
    })
  ];
}

module.exports = config;
