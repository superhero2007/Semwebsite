/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main', [
    'ui.router',

    'BlurAdmin.main.trading',
    'BlurAdmin.main.network'
  ]).config(routeConfig);

  /** @ngInject */
  function routeConfig($urlRouterProvider, baSidebarServiceProvider, $locationProvider) {
    $urlRouterProvider.otherwise('/trading/dashboard');
    $locationProvider.html5Mode(true);
  }

})();