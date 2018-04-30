/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.correlation.table', [])
        .config(routeConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('dashboard.correlation.table', {
                url: '/table',
                templateUrl: 'app/main/dashboard/correlation/table/table.html',
                controller: 'TableController',
                title: 'Table',
                sidebarMeta: {
                    icon: '',
                    order: 200,
                },
            });
    }

    angular.module('BlurAdmin.main.dashboard.correlation.table')
        .factory('TableService', function ($http) {
            return {
                getData: function () {
                    return $http.get('/api/Network').then(function (result) {
                        return result.data
                    });
                }
            }
        });

    angular.module('BlurAdmin.main.dashboard.correlation.table')
        .controller('DailyController', function ($scope, $timeout, DailyService) {
            $scope.standardItem = {};
            $scope.standardSelectItems = [
                {label: 'Option 1', value: 1},
                {label: 'Option 2', value: 2},
                {label: 'Option 3', value: 3},
                {label: 'Option 4', value: 4}
            ];
        });

})();
