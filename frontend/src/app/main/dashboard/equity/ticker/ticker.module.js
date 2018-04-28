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
                params: {
                    obj: null
                }
            })
    }

    angular.module('BlurAdmin.main.dashboard.equity.ticker')
        .factory('TickerService', function ($http) {
            return {
                getData: function (ticker) {
                    return $http.post('/api/Equity/Ticker/', {ticker: ticker}).then(function (result) {
                        return result.data
                    });
                }
            };
        });

    angular.module('BlurAdmin.main.dashboard.equity.ticker')
        .controller('TickerController', function ($scope, $stateParams, TickerService) {
            $scope.filterParameter = $stateParams.obj;
            $scope.filter = {
                ticker: ''
            };
            if ($scope.filterParameter) {
                TickerService.getData($scope.filterParameter).then(function (data) {
                    $scope.tickerData = data.data;
                })
            }
            $scope.filter_ticker = function () {
                if ($scope.filter.ticker != '') {
                    TickerService.getData($scope.filter.ticker).then(function (data) {
                        $scope.tickerData = data.data;
                    })
                } else {
                    $scope.tickerData = [];
                }
            }
        });
})();