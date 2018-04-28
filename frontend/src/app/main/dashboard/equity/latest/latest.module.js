  /**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.latest', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.equity.latest', {
        url: '/latest',
        templateUrl: 'app/main/dashboard/equity/latest/latest.html',
        controller: 'LatestController',
        title: 'Latest',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
  }

  angular.module('BlurAdmin.main.dashboard.equity.latest')
    .factory('LatestService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Equity/Latest').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.dashboard.equity.latest')
    .controller('LatestController', function($scope, $state, LatestService) {
      LatestService.getData().then(function(data) {
        $scope.latestData = data.data;
      })
      $scope.showGraph = function(ticker) {
        $state.go('dashboard.equity.ticker', {obj: ticker})
      }
    });
})();