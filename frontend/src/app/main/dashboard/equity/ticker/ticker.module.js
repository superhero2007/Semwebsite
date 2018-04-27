  /**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.ticker', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.equity.ticker', {
        url: '/ticker',
        templateUrl: 'app/main/dashboard/equity/ticker/ticker.html',
        controller: 'TickerController',
        title: 'Ticker Search',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
  }

  angular.module('BlurAdmin.main.dashboard.equity.ticker')
    .factory('TickerService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Equity/Ticker/A/').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.dashboard.equity.ticker')
    .controller('TickerController', function($scope, TickerService) {
      TickerService.getData().then(function(data) {
        $scope.tickerData = data.data;
      })
    });
})();