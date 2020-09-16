function stateConfig(
  $locationProvider,
  $stateProvider,
  $urlRouterProvider) {
  $stateProvider
    .state('main', {
      template: '<mont-main></mont-main>',
    })
    .state('main.dashboard', {
      url: '/',
      template: '<mont-dashboard></mont-dashboard>',
    })
    .state('main.campaigns-all', {
      url: '/campaigns/all',
      template: '<mont-campaigns-all></mont-campaigns-all>',
    })
    .state('main.campaign-new', {
      url: '/campaign/new',
      template: '<mont-campaign-new></mont-campaign-new>',
    })
    .state('main.campaign', {
      url: '/campaign/:id',
      template: '<mont-campaign></mont-campaign>',
    })
    .state('main.vote-faves', {
      url: '/vote/faves',
      template: '<mont-vote-faves></mont-vote-faves>',
    })
    .state('main.vote', {
      url: '/vote/:id',
      template: '<mont-vote data="$resolve.round" tasks="$resolve.tasks"></mont-vote>',
      resolve: {
        round: ($stateParams, jurorService) => jurorService.getRound($stateParams.id.split('-')[0]),
        tasks: ($stateParams, jurorService) => jurorService.getRoundTasks($stateParams.id.split('-')[0]),
      },
    })
    .state('main.vote-edit', {
      url: '/vote/:id/edit',
      template: '<mont-vote-edit data="$resolve.round"></mont-vote-edit>',
      resolve: {
        round: ($stateParams, jurorService) => jurorService.getRoundVotesStats($stateParams.id.split('-')[0]),
      },
    });

  $urlRouterProvider.otherwise('/');
  // $locationProvider.html5Mode(true);

/*
    .state('main.juror', {
      template: '<ui-view></ui-view>',
      resolve: {
        data: (userService) => userService.juror.get(),
        userType: ($q) => $q.when('juror')
      },
      onEnter: ($state, data) => {
        console.log('ENTER MAIN JUROR');
        // invalid cookie userid, try logging in again
        if (data.status === 'failure' && data.errors.length) {
          $state.go('main.login');
        }
      }
    })
    .state('main.juror.dashboard', {
      url: '/',
      template: `<mont-dashboard
                      layout="column" layout-align="start start"
                      data="$resolve.data"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-dashboard>`,
    })
    .state('main.juror.round', {
      url: '/round/:id',
      template: `<mont-round
                      layout="column" layout-align="start start"
                      data="$resolve.round"
                      user="$resolve.user"
                      tasks="$resolve.tasks"
                      type="$resolve.userType"></mont-round>`,
      resolve: {
        round: ($stateParams, userService) => userService.juror.getRound($stateParams.id),
        tasks: ($stateParams, userService) => userService.juror.getRoundTasks($stateParams.id)
      }
    })
    .state('main.juror.vote-edit', {
      url: '/round/:id/edit',
      template: `<mont-vote-edit
                      layout="column" layout-align="start start"
                      data="$resolve.round"
                      user="$resolve.user"
                      tasks="$resolve.tasks"
                      type="$resolve.userType"></mont-round>`,
      resolve: {
        round: ($stateParams, userService) => userService.juror.getRound($stateParams.id),
        tasks: ($q, $stateParams, userService) => {
          let votes = {
            rating: userService.juror.getPastVotes($stateParams.id),
            ranking: userService.juror.getPastRanking($stateParams.id)
          };
          return $q.all(votes).then((response) => response.rating.data.length ? response.rating : response.ranking);
        }
      }
    })
*/

/*
    .state('main.admin', {
      template: '<ui-view></ui-view>',
      resolve: {
        data: (userService) => userService.admin.get(),
        userType: ($q) => $q.when('admin')
      },
      onEnter: ($state, data) => {
        //invalid cookie userid, try logging in again
        if (data.status === 'failure' && data.errors.length) {
          $state.go('main.login');
        }
      }
    })
    .state('main.admin.dashboard', {
      url: '/admin',
      template: `<mont-dashboard
                      layout="column" layout-align="start start"
                      data="$resolve.data"
                      user="$resolve.user"
                      type="$resolve.userType"></mont-dashboard>`
    })
    .state('main.login', {
      url: '/login',
      template: `<mont-login
                      layout="column" layout-align="center center"
                      data="$resolve.data"></mont-login>`,
      resolve: {
        data: (userService) => userService.juror.get()
      },
    });
  $urlRouterProvider.otherwise('/');
*/
}

export default stateConfig;
