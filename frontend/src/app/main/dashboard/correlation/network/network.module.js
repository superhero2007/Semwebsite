/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.correlation.network', [])
        .config(routeConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('dashboard.correlation.network', {
                url: '/network',
                templateUrl: 'app/main/dashboard/correlation/network/network.html',
                controller: 'NetworkController',
                title: 'Network',
                sidebarMeta: {
                    icon: '',
                    order: 200,
                },
            });
    }

    angular.module('BlurAdmin.main.dashboard.correlation.network')
        .factory('NetworkService', function ($http) {
            return {
                getData: function (barSelectedItem, loopbackSelectedItem, correlation) {
                    return $http.post('api/Correlation/View/', {
                        aggregation: barSelectedItem,
                        lookback: loopbackSelectedItem,
                        corr_threshold: correlation,
                        graph: 1
                    }).then(function (result) {
                        return result.data
                    });
                }
            }
        });

    angular.module('BlurAdmin.main.dashboard.correlation.network')
        .controller('NetworkController', function ($scope, $timeout, NetworkService) {
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
            $scope.filterData = function () {
                NetworkService.getData($scope.barSelectedItem.selected.value, $scope.loopbackSelectedItem.selected.value, $scope.filter.correlation).then(function (data) {
                    $scope.my_nodes = data.nodes;
                    $scope.my_edges = data.edges;
                    startup_network()
                });
            };

            $scope.empty_edges = null;
            $scope.edges_delay_var = 0;
            $scope.options = {};
            $scope.filter = {
                weight: 0.5,
                ticker: ''
            };

            function startup_network() {
                $scope.nodes = new vis.DataSet($scope.my_nodes);
                $scope.edges = new vis.DataSet($scope.empty_edges);
                $scope.data = {
                    nodes: $scope.nodes,
                    edges: $scope.edges
                };
                $scope.container = document.getElementById('mynetwork');
                $scope.network = new vis.Network($scope.container, $scope.data, $scope.options);
                $scope.network.setOptions({
                    physics: {enabled: true}
                });

                $scope.options = {physics: true};

                $scope.edges_delay_var = $timeout(function () {
                    add_edges()
                }, 3000);
            }

            function add_edges() {
                $scope.data = {
                    nodes: $scope.my_nodes,
                    edges: $scope.empty_edges
                };
                for (var i = 0; i < $scope.my_edges.length; i++) {
                    $scope.edges.add($scope.my_edges[i]);
                }
                clearTimeout($scope.edges_delay_var);
                $scope.edges_delay_var = $timeout(function () {
                    stop_animation()
                }, 6000);
            }

            function stop_animation() {
                $scope.network.setOptions({
                    physics: {enabled: false}
                });
                clearTimeout($scope.edges_delay_var);
            }
        });

})();
