var path = require('path');
var webpack = require('webpack');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var ngAnnotatePlugin = require('ng-annotate-webpack-plugin');

var config = {
  context: path.join(__dirname, 'app'),
  entry: './index.js',
  output: {
    path: path.join(__dirname, '..', 'montage', 'static', 'assets'),
    publicPath: 'assets/',
    filename: 'bundle.js'
  },
  plugins: [new HtmlWebpackPlugin({
    template: 'index_local.ejs',
    filename: path.join('..', 'index.html')
  })],
  devtool: 'source-map',
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
        test: /\.(woff|woff2|ttf|eot)$/,
        loader: 'file?name=fonts/[name].[ext]'
      },
      {
        test: /\.(jpe?g|png|gif|svg)$/i,
        loader: 'file?name=images/[name].[ext]'
      },
      {
        test: /\.json$/, loader: 'json'
      }
    ]
  }
};

var ENV = process.env.NODE_ENV;
if (ENV === 'prod' || ENV === 'dev' || ENV === 'beta') {
  config.output = {
    path: path.join(__dirname, '..', 'montage', 'static', 'dist'),
    publicPath: 'dist/',
    filename: 'bundle.min.js'
  };
  config.plugins = [
    new HtmlWebpackPlugin({
      template: ENV === 'dev' ? 'index_dev.ejs' : ENV === 'beta' ? 'index_beta.ejs' : 'index_prod.ejs',
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
