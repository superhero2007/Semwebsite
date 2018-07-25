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
                title: 'Sector / Industry',
                sidebarMeta: {
                    icon: '',
                    order: 100,
                },
            })
    }

    angular.module('BlurAdmin.main.dashboard.equity.sector')
        .factory('SectorService', function ($http) {
            return {
                getData: function () {
                    return $http.get('/api/Equity/SecInd/').then(function (result) {
                        return result.data
                    });
                },
                getSector: function (sector) {
                    return $http.post('/api/Equity/Sector/', {sector: sector}).then(function (result) {
                        return result.data
                    });
                },
                getIndustry: function (industry) {
                    return $http.post('/api/Equity/Industry/', {industry: industry}).then(function (result) {
                        return result.data
                    });
                }
            };
        });

    angular.module('BlurAdmin.main.dashboard.equity.sector')
        .controller('SectorController', function ($scope, $state, SectorService) {
            SectorService.getData().then(function (data) {
                $scope.exposuresData = data.data.sort(function (a, b) {
                    if (a.Sector > b.Sector) return 1;
                    if (a.Sector < b.Sector) return -1;
                    if (a.Industry == 'All') return -1;
                    if (b.Industry == 'All') return 1;
                });
            });
            $scope.headers = [];
            $scope.filterData = [];
            $scope.title = '';
            $scope.collapse = function (entry) {
                if (entry.Industry != 'All') {
                    return
                }
                var entryObj = $scope.headers.find(function (obj) {
                    return obj == entry.Sector
                });
                if (entryObj) {
                    $scope.headers = $scope.headers.filter(function (obj) {
                        return obj !== entryObj
                    })
                } else {
                    $scope.headers.push(entry.Sector)
                }
            };
            $scope.showSector = function (sector) {
                SectorService.getSector(sector).then(function (data) {
                    $scope.rowCollection = data.data;
                    $scope.filterData = [].concat($scope.rowCollection);
                    $scope.title = sector;
                })
            };
            $scope.showIndustry = function (industry) {
                SectorService.getIndustry(industry).then(function (data) {
                    $scope.rowCollection = data.data;
                    $scope.filterData = [].concat($scope.rowCollection);
                    $scope.title = industry;
                })
            };
            $scope.showGraph = function (ticker) {
                $state.go('dashboard.equity.ticker', {obj: ticker})
            };
        });
})();
