/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('trading', {
        url: '/trading',
        template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
        abstract: true,
        title: 'Trading',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
      .state('trading.dashboard', {
        url: '/dashboard',
        templateUrl: 'app/main/trading/trading.html',
        controller: 'TradingController',
        title: 'Dashboard',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      });
  }

  angular.module('BlurAdmin.main.trading')
    .factory('TradingService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Dashboard').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.trading')
    .controller('TradingController', function($scope, TradingService) {
      TradingService.getData().then(function(data) {
        $scope.tradingData = data;
      })
    });


})();
