/**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.trading.exposures', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.trading.exposures', {
        url: '/exposures',
        templateUrl: 'app/main/dashboard/trading/exposures/exposures.html',
        controller: 'ExposuresController',
        title: 'Exposures',
        sidebarMeta: {
          icon: '',
          order: 100,
        },
      })
  }

  angular.module('BlurAdmin.main.dashboard.trading.exposures')
    .factory('ExposuresService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Exposures').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.dashboard.trading.exposures')
    .controller('ExposuresController', function($scope, ExposuresService) {
      ExposuresService.getData().then(function(data) {
        $scope.exposuresData = data.data.sort(function (a, b) {
          if (a.Sector > b.Sector) return 1;
          if (a.Sector < b.Sector) return -1;
          if (a.Industry == 'All') return -1;
          if (b.Industry == 'All') return 1;
        });
      })
      $scope.headers = []
      $scope.collapse = function(entry) {
        if(entry.Industry != 'All') {
          return
        }
        console.log(entry)
        var entryObj = $scope.headers.find(function(obj) {
          return obj == entry.Sector
        })
        if (entryObj) {
          $scope.headers = $scope.headers.filter(function(obj){
            return obj !== entryObj
          })
        } else {
          $scope.headers.push(entry.Sector)
        }
        console.log($scope.headers)
      }
    });
})();
