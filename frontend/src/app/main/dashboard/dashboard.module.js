/**
 * @author v.lugovsky
 * created on 16.12.2015
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard', [])
      .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
        .state('dashboard', {
          url: '/Trading/Dashboard',
          templateUrl: 'app/main/dashboard/dashboard.html',
          controller: 'DashboardController',
          title: 'Dashboard',
          sidebarMeta: {
            icon: 'ion-android-home',
            order: 0,
          },
        });
  }

  angular.module('BlurAdmin.main.dashboard')
    .factory('DashboardService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Dashboard').then(function(result) {
            return result.data
          });
        }
      };
    });

  angular.module('BlurAdmin.main.dashboard')
    .controller('DashboardController', function($scope, DashboardService) {
      DashboardService.getData().then(function(data) {
        $scope.dashboardData = data;
      })
    });


})();
