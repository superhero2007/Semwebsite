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
        .factory('LatestService', function ($http) {
            return {
                getData: function () {
                    return $http.get('/api/Equity/Latest').then(function (result) {
                        return result.data
                    });
                }
            };
        });

    angular.module('BlurAdmin.main.dashboard.equity.latest')
        .controller('LatestController', function ($scope, $state, LatestService) {
            LatestService.getData().then(function (data) {
                $scope.latestData = data.data;
            });
            $scope.showGraph = function (ticker) {
                $state.go('dashboard.equity.ticker', {obj: ticker})
            };
            $scope.sortKey = '';
            $scope.ref = 1;
            $scope.setSort = function (sortKey) {
                $scope.ref = -$scope.ref;
                if ($scope.sortKey !== sortKey)
                    $scope.ref = 1;
                $scope.sortKey = sortKey;
                $scope.latestData = $scope.latestData.sort(function (a, b) {
                    let ref = $scope.ref;
                    if (sortKey == 'ticker') {
                        if (a.ticker > b.ticker) return ref;
                        else return -ref;
                    }
                    if (sortKey == 'sector') {
                        if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return ref;
                        else return -ref;
                    }
                    if (sortKey == 'industry') {
                        if (a.zacks_m_ind_desc > b.zacks_m_ind_desc) return ref;
                        else return -ref;
                    }
                    if (sortKey == 'signal') {
                        if (a.SignalConfidence > b.SignalConfidence) return ref;
                        else return -ref;
                    }
                    return -1;
                });
            }
        });
})();