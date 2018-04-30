/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.correlation.table', ['ui.select', 'ngSanitize'])
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
                    order: 100,
                },
            });
    }

    angular.module('BlurAdmin.main.dashboard.correlation.table')
        .factory('TableService', function ($http) {
            return {
                getData: function (barSelectedItem, loopbackSelectedItem, correlation) {
                    return $http.post('api/Correlation/View/', {
                        aggregation: barSelectedItem,
                        lookback: loopbackSelectedItem,
                        corr_threshold: correlation,
                        graph: 0
                    }).then(function (result) {
                        return result.data
                    });
                }
            }
        });

    angular.module('BlurAdmin.main.dashboard.correlation.table')
        .controller('TableController', function ($scope, $timeout, TableService) {
            $scope.barSelectedItem = {};
            $scope.barSizeItems = [
                {label: '1 Minutes', value: 1},
                {label: '5 Minutes', value: 5},
                {label: '15 Minutes', value: 15},
                {label: '30 Minutes', value: 30},
                {label: '60 Minutes', value: 60}
            ];
            $scope.filter = {
                correlation: 0
            };
            $scope.loopbackSelectedItem = {};
            $scope.loopbackItems = [
                {label: '1 Week', value: '1week'},
                {label: '1 Month', value: '1month'},
                {label: '1 Qtr', value: '1qtr'}
            ];
            $scope.tableData = [];
            $scope.filterData = function () {
                TableService.getData($scope.barSelectedItem.selected.value, $scope.loopbackSelectedItem.selected.value, $scope.filter.correlation).then(function (data) {
                    $scope.tableData = data.data;
                });
            };
        });

})();
