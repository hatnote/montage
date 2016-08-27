import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import './vendor/css/bootstrap.css';
import Round from './admin/round';

function onImport() {
    console.log('waaaa!');
}
const App = () => (
    <div>
      <div className="navbar navbar-inverse">
        <div className='container'>
          <div className='navbar-header'>
            <a className='navbar-brand'>Yet Another Jury Tool</a>
          </div>
          <div className='collapse navbar-collapse pull-right'>
            <ul className='nav navbar-nav'>
              <li><a href='//localhost:5000/login'>Login</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div className='container'>
        <div className='row'>
            <Round onImportFromCommons={onImport}/>
        </div>
      </div>
      </div>
)

export default App;
