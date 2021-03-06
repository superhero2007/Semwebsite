/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard', [
    'BlurAdmin.main.dashboard.trading',
    'BlurAdmin.main.dashboard.correlation',
    'BlurAdmin.main.dashboard.equity',
    'BlurAdmin.main.dashboard.factor'
  ])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard', {
        url: '/dashboard',
        templateUrl: 'app/main/dashboard/dashboard.html',
        title: 'Dashboard',
        redirectTo: 'dashboard.equity.latest'
   	})
  }

})();
