  /**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading.dashboard', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('trading.dashboard', {
        url: '/dashboard',
        templateUrl: 'app/main/trading/dashboard/dashboard.html',
        controller: 'DashboardController',
        title: 'Dashboard',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      });
  }

  angular.module('BlurAdmin.main.trading.dashboard')
    .factory('DashboardService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Dashboard').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.trading.dashboard')
    .controller('DashboardController', function($scope, DashboardService) {
      DashboardService.getData().then(function(data) {
        $scope.tradingData = data;
      })
    });
})();