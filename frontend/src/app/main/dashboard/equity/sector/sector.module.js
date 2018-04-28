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
            $scope.sectorData = [];
            $scope.industryData = [];
            $scope.collapse = function (entry) {
                if (entry.zacks_m_ind_desc != 'All') {
                    return
                }
                console.log(entry)
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
                console.log($scope.headers)
            };
            $scope.showSector = function (sector) {
                SectorService.getSector(sector).then(function (data) {
                    $scope.sectorData = data.data.sort(function (a, b) {
                        if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
                        if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
                        if (a.zacks_m_ind_desc == 'All') return -1;
                        if (b.zacks_m_ind_desc == 'All') return 1;
                    });
                })
            };
            $scope.showIndustry = function (industry) {
                SectorService.getIndustry(industry).then(function (data) {
                    $scope.industryData = data.data.sort(function (a, b) {
                        if (a.zacks_x_sector_desc > b.zacks_x_sector_desc) return 1;
                        if (a.zacks_x_sector_desc < b.zacks_x_sector_desc) return -1;
                        if (a.zacks_m_ind_desc == 'All') return -1;
                        if (b.zacks_m_ind_desc == 'All') return 1;
                    });
                })
            }
            $scope.showGraph = function (ticker) {
                $state.go('dashboard.equity.ticker', {obj: ticker})
            }
        });
})();