import angular from 'angular';
import moment from 'moment';

import 'angular-material';
import 'angular-translate';
import 'angular-ui-router';
import 'ng-infinite-scroll';

import 'angular-chart.js';

import 'angular-material/angular-material.css';
import 'material-design-icons/iconfont/material-icons.css';
import './style.scss';

import { httpConfig, localeConfig, themeConfig } from './app.config';
import { translateConfig } from './app.l10n';
import stateConfig from './app.routing';

import main from './components/main/main';
import campaign from './components/campaign/campaign.component';
import round from './components/campaign/round/round.component';
import roundEdit from './components/campaign/round-edit/round-edit.component';
import roundNew from './components/campaign/round-new/round-new.component';

import campaignNew from './components/campaign-new/campaign-new.component';
import campaignOld from './components/campaign-old/campaign';

import dashboard from './components/dashboard/dashboard';
import all_campaigns from './components/dashboard/all_campaigns';
import campaignAdminBox from './components/dashboard/campaign-admin-box/campaign-admin-box.component';
import campaignJurorBox from './components/dashboard/campaign-juror-box/campaign-juror-box.component';
import footer from './components/footer/footer.component';

import vote from './components/vote/vote.component';
import votebox from './components/vote/votebox/votebox.component';
import voteRanking from './components/vote/vote-ranking/vote-ranking.component';
import voteSingle from './components/vote/vote-single/vote-single.component';
import voteEdit from './components/vote-edit/vote-edit';
import voteFaves from './components/vote-faves/vote-faves';

import login from './components/login/login.component';
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
    'chart.js',
    'infinite-scroll',
    'pascalprecht.translate',
  ])
  .config(httpConfig)
  .config(stateConfig)
  .config(themeConfig)
  .config(localeConfig)
  .config(translateConfig)
  .config(function($sceDelegateProvider) {
    $sceDelegateProvider.trustedResourceUrlList([
      'self',
      'https://commons.wikimedia.org/**'
    ])
  })

  .component('montMain', main)
  .component('montCampaign', campaign)
  .component('montRound', round)
  .component('montRoundEdit', roundEdit)
  .component('montRoundNew', roundNew)

  .component('montCampaignNew', campaignNew)
  .component('montCampaignOld', campaignOld)
  .component('montCampaignAdminBox', campaignAdminBox)
  .component('montCampaignJurorBox', campaignJurorBox)
  .component('montDashboard', dashboard)
  .component('montCampaignsAll', all_campaigns)
  .component('montFooter', footer)

  .component('montVote', vote)
  .component('montVotebox', votebox)
  .component('montVoteRanking', voteRanking)
  .component('montVoteSingle', voteSingle)
  .component('montVoteEdit', voteEdit)
  .component('montVoteFaves', voteFaves)

  .component('montLogin', login)
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
  .filter('fromNow', () => input => moment.utc(input).add(1, 'day').fromNow());
