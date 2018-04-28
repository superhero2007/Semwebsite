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
                    if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
                    if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
                    if (a.zacks_m_ind_desc == 'All') return -1;
                    if (b.zacks_m_ind_desc == 'All') return 1;
                });
            });
            $scope.headers = [];
            $scope.filterData = [];
            $scope.title = '';
            $scope.collapse = function (entry) {
                if (entry.zacks_m_ind_desc != 'All') {
                    return
                }
                var entryObj = $scope.headers.find(function (obj) {
                    return obj == entry.zacks_x_sector_desc
                });
                if (entryObj) {
                    $scope.headers = $scope.headers.filter(function (obj) {
                        return obj !== entryObj
                    })
                } else {
                    $scope.headers.push(entry.zacks_x_sector_desc)
                }
            };
            $scope.showSector = function (sector) {
                SectorService.getSector(sector).then(function (data) {
                    $scope.filterData = data.data.sort(function (a, b) {
                        if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
                        if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
                        if (a.zacks_m_ind_desc == 'All') return -1;
                        if (b.zacks_m_ind_desc == 'All') return 1;
                    });
                    $scope.title = sector;
                })
            };
            $scope.showIndustry = function (industry) {
                SectorService.getIndustry(industry).then(function (data) {
                    $scope.filterData = data.data.sort(function (a, b) {
                        if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
                        if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
                        if (a.zacks_m_ind_desc == 'All') return -1;
                        if (b.zacks_m_ind_desc == 'All') return 1;
                    });
                    $scope.title = industry;
                })
            };
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
                $scope.filterData = $scope.filterData.sort(function (a, b) {
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