  /**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.sector', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.equity.sector', {
        url: '/sector',
        templateUrl: 'app/main/dashboard/equity/sector/sector.html',
        controller: 'SectorController',
        title: 'Sector/Industry',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
  }

  angular.module('BlurAdmin.main.dashboard.equity.sector')
    .factory('SectorService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Exposures').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.dashboard.equity.sector')
    .controller('SectorController', function($scope, SectorService) {
      SectorService.getData().then(function(data) {
        $scope.exposuresData = data.data.sort(function (a, b) {
          if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
          if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
          if (a.zacks_m_ind_desc == 'All') return -1;
          if (b.zacks_m_ind_desc == 'All') return 1;
        });
      })
      $scope.headers = []
      $scope.collapse = function(entry) {
        if(entry.zacks_m_ind_desc != 'All') {
          return
        }
        console.log(entry)
        var entryObj = $scope.headers.find(function(obj) {
          return obj == entry.zacks_x_sector_desc
        })
        if (entryObj) {
          $scope.headers = $scope.headers.filter(function(obj){
            return obj !== entryObj
          })
        } else {
          $scope.headers.push(entry.zacks_x_sector_desc)
        }
        console.log($scope.headers)
      }
    });
})();