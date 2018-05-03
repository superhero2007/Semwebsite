/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.factor', [])
        .config(routeConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('dashboard.factor', {
                url: '/factor',
                templateUrl: 'app/main/dashboard/factor/factor.html',
                controller: 'FactorController',
                title: 'Factor Returns',
                sidebarMeta: {
                    icon: '',
                    order: 200,
                },
            });
    }

    angular.module('BlurAdmin.main.dashboard.factor')
        .factory('FactorService', function ($http) {
            return {
                getData: function (start_date, end_date) {
                    return $http.post('api/Factor/', {
                        start_date: start_date,
                        end_date: end_date
                    }).then(function (result) {
                        return result.data
                    });
                }
            }
        });

    angular.module('BlurAdmin.main.dashboard.factor')
        .controller('FactorController', function ($scope, $timeout, FactorService) {
            $scope.date = {
              start_date: '',
              end_date: ''
            };
            FactorService.getData($scope.date.start_date, $scope.date.end_date).then(function (data) {
                $scope.available_dates = data.available_dates;
                $scope.data = data.data;
                $scope.factors = data.factors;
                console.log($scope.available_dates);
                console.log($scope.data);
                console.log($scope.factors);
            });
        });

})();
