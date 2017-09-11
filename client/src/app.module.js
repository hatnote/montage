import angular from 'angular';
import moment from 'moment';

import 'angular-material';
import 'angular-ui-router';
import 'ng-infinite-scroll';

import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';
import './style.scss';

import { httpConfig, localeConfig, themeConfig } from './app.config';
import stateConfig from './app.routing';

import main from './components/main/main';
import campaign from './components/campaign/campaign.component';
import campaignOld from './components/campaign-old/campaign';

import dashboard from './components/dashboard/dashboard';
import campaignAdminBox from './components/dashboard/campaign-admin-box/campaign-admin-box.component';

import round from './components/round/round';
import login from './components/login/login';
import voteEdit from './components/vote-edit/vote-edit';
import userList from './components/user-list';
import toolbar from './components/toolbar/toolbar.component';
import './components/angular-sortable-view';

import avatarDirective from './directives/avatar.directive';
import keyActionsDirective from './directives/key-actions.directive';
import srcDirective from './directives/src.directive';

import adminService from './services/admin.service';
import alertService from './services/alert.service';
import dataService from './services/data.service';
import dialogService from './services/dialog.service';
import errorService from './services/error.service';
import jurorService from './services/juror.service';
import userService from './services/user.service';
import versionService from './services/version.service';

import { ordinal } from './services/filters';

angular.module('montage',
  [
    'ngMaterial',
    'ui.router',
    'angular-sortable-view',
    'infinite-scroll',
  ])
  .config(httpConfig)
  .config(stateConfig)
  .config(themeConfig)
  .config(localeConfig)

  .component('montMain', main)
  .component('montCampaign', campaign)
  .component('montCampaignOld', campaignOld)
  .component('montCampaignAdminBox', campaignAdminBox)
  .component('montDashboard', dashboard)
  .component('montRound', round)
  .component('montLogin', login)
  .component('montVoteEdit', voteEdit)
  .component('montUserList', userList)
  .component('montToolbar', toolbar)

  .directive('montAvatar', avatarDirective)
  .directive('montKeyActions', keyActionsDirective)
  .directive('montSrc', srcDirective)

  .factory('adminService', adminService)
  .factory('alertService', alertService)
  .factory('dataService', dataService)
  .factory('dialogService', dialogService)
  .factory('errorService', errorService)
  .factory('jurorService', jurorService)
  .factory('userService', userService)
  .factory('versionService', versionService)

  .filter('ordinal', ordinal)
  .filter('fromNow', () => input => moment.utc(input).fromNow());
