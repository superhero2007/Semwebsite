/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main', [
    'BlurAdmin.main.login',
    'BlurAdmin.main.dashboard'
  ]).config(routeConfig);

  /** @ngInject */
  function routeConfig($urlRouterProvider, baSidebarServiceProvider, $locationProvider) {
    $urlRouterProvider.otherwise('/login');
    // $locationProvider.html5Mode(true);
  }

  angular.module('BlurAdmin.main')
    .run(['$rootScope', '$location', '$cookies', '$http', '$state',
      function ($rootScope, $location, $cookies, $http, $state) {
        $http.defaults.xsrfCookieName = 'csrftoken';
        $http.defaults.xsrfHeaderName = 'X-CSRFToken';
        // keep user logged in after page refresh
        $rootScope.globals = $cookies.get('globals') || {};
        if ($rootScope.globals.currentUser) {
            // $http.defaults.headers.common['Authorization'] = 'Basic ' + $rootScope.globals.currentUser.authdata; // jshint ignore:line
        }

        $rootScope.$on('$stateChangeStart', function (event, next, current) {
            // redirect to login page if not logged in
            if (next.name !== 'login' && !$rootScope.globals.currentUser) {
              // $state.go('login')
              // event.preventDefault();
            }
        });
      }]);

})();
