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
                    order: 100,
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
            $scope.barSelectedItem = {
                selected: {label: '60 Minutes', value: 60}
            };
            $scope.barSizeItems = [
                {label: '1 Minutes', value: 1},
                {label: '5 Minutes', value: 5},
                {label: '15 Minutes', value: 15},
                {label: '30 Minutes', value: 30},
                {label: '60 Minutes', value: 60}
            ];
            $scope.loopbackSelectedItem = {
                selected: {label: '1 Qtr', value: '1qtr'}
            };
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
                ticker: '',
                correlation: 0.6
            };
            $scope.filterData();

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

            $scope.show_complete_chart = function () {
                $scope.filter = {
                    ticker: "",
                    weight: 0.5,
                    correlation: 0.6
                };
                startup_network();
            };

            $scope.filter_weight = function () {
                var test_value = $scope.filter.weight;
                var m_nodes = $scope.my_nodes;
                var m_edges = $scope.my_edges;
                var position = 200;
                var child_num = 0;
                var new_child;

                test_value = parseFloat(test_value) * 10.0;
                //var test_value="AXP";

                var new_nodes = [];
                var new_edges = [];
                // console.log("m_edges "+m_edges.length);
                for (var i = 0; i < m_edges.length; i++) {
                    // console.log("weight "+(m_edges[i].width) + " " + test_value );
                    if (parseFloat(m_edges[i].width) >= test_value) {
                        // console.log("m_edges "+m_edges[i]);
                        position += 5;
                        m_edges[i].x = position;
                        new_edges.push(m_edges[i]);

                        var findObj = new_nodes.find(
                            function (obj) {
                                return obj.id == m_edges[i].to
                            }
                        );
                        if (!findObj) {
                            new_child = m_nodes.find(function (obj) {
                                return obj.id == m_edges[i].to
                            });
                            // console.log(new_child.label);
                            new_child.x = position + child_num * 2
                            new_child.y = position + child_num * 2
                            new_nodes.push(new_child);
                            //new_nodes.push(m_nodes.find(obj=>obj.id==m_edges[i].to));
                        }
                        if (!new_nodes.find(function (obj) {
                            return obj.id == m_edges[i].from
                        })) {
                            new_child = m_nodes.find(function (obj) {
                                return obj.id == m_edges[i].from
                            });
                            // console.log(new_child.label);
                            new_child.x = position + child_num * 2
                            new_child.y = position + child_num * 2
                            new_nodes.push(new_child);
                            //new_nodes.push(m_nodes.find(obj=>obj.id==m_edges[i].from));
                        }
                    }
                }

                $scope.data = {
                    nodes: new_nodes,
                    edges: new_edges
                };
                $scope.network = new vis.Network($scope.container, $scope.data, {});
                // $scope.edges_delay_var=setTimeout(stop_animation, 3000);
            };

            $scope.filter_company = function () {
                var test_value = $scope.filter.ticker;
                var m_nodes = $scope.network.body.nodes;
                for (var i in m_nodes) {
                    if (m_nodes[i].options.label.toLowerCase() == test_value.toLowerCase()) {
                        $scope.network.focus(i, {scale: 3});
                        console.log(m_nodes[i])
                    }
                }
            }
        });

})();
