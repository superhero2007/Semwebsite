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
        templateUrl: 'app/main/trading/trading.html',
        controller: 'TradingController',
        title: 'Trading',
        sidebarMeta: {
          icon: 'ion-android-home',
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
