/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.network', [])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('network', {
        url: '/network',
        templateUrl: 'app/main/network/network.html',
        controller: 'NetworkController',
        title: 'Correlation',
        sidebarMeta: {
          icon: '',
          order: 100,
        },
      });
  }

  angular.module('BlurAdmin.main.network')
    .factory('NetworkService', function($http) {
      return {
        getData: function () {
          return $http.get('/api/Trading/Network').then(function(result) {
            return result.data
          });
        }
      }
    });

  angular.module('BlurAdmin.main.network')
    .controller('NetworkController', function($scope, $timeout, NetworkService) {
      NetworkService.getData().then(function(data) {
        $scope.my_nodes = data.my_nodes;
        $scope.my_edges = data.my_edges;
        startup_network()
      })


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
          physics: {enabled:true}
        });

        $scope.options = { physics: true };

        $scope.edges_delay_var=$timeout(function () {add_edges()}, 3000);
      }

      function add_edges() {
        $scope.data = {
          nodes: $scope.my_nodes,
          edges: $scope.empty_edges
        };
        for (var i=0;i<$scope.my_edges.length;i++) {
          $scope.edges.add($scope.my_edges[i]);
        }
        clearTimeout($scope.edges_delay_var);
        $scope.edges_delay_var=$timeout(function () {stop_animation()}, 6000);
      }
      function stop_animation() {
        $scope.network.setOptions({
          physics: {enabled:false}
        });
        clearTimeout($scope.edges_delay_var);
      }

      $scope.show_complete_chart = function () {
        $scope.filter = {
          ticker: "",
          weight: 0.5
        }
        startup_network();
      }

      $scope.filter_weight = function () {
        var test_value = $scope.filter.weight;
        var m_nodes=$scope.my_nodes;
        var m_edges=$scope.my_edges;
        var position=200;
        var child_num=0;
        var new_child;
        
        test_value=parseFloat(test_value) * 10.0;
        //var test_value="AXP";
        
        var new_nodes= [];
        var new_edges= [];
        // console.log("m_edges "+m_edges.length);
        for (var i=0; i < m_edges.length; i++) {
          // console.log("weight "+(m_edges[i].width) + " " + test_value );
          if (parseFloat(m_edges[i].width) >= test_value ) {
            // console.log("m_edges "+m_edges[i]);
            position+=5;  
            m_edges[i].x=position;
            new_edges.push(m_edges[i]);
            
            var findObj = new_nodes.find(
              function(obj) { 
                return obj.id == m_edges[i].to
              }
            );
            if (!findObj) {
              new_child=m_nodes.find( function(obj) { return obj.id==m_edges[i].to });
              // console.log(new_child.label);       
              new_child.x=position+child_num*2
              new_child.y=position+child_num*2
              new_nodes.push(new_child);
              //new_nodes.push(m_nodes.find(obj=>obj.id==m_edges[i].to));
            } 
            if (!new_nodes.find(function(obj) { return obj.id==m_edges[i].from })) {
              new_child=m_nodes.find(function(obj) { return obj.id==m_edges[i].from });
              // console.log(new_child.label); 
              new_child.x=position+child_num*2
              new_child.y=position+child_num*2
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
      } 

      $scope.filter_company = function () {
        var test_value = $scope.filter.ticker;
        var m_nodes = $scope.network.body.nodes;
        for (var i in m_nodes) {
          if (m_nodes[i].options.label.toLowerCase() == test_value.toLowerCase() ) {
            $scope.network.focus(i, {scale: 3});
            console.log(m_nodes[i])
          }
        }
        /* var test_value = $scope.filter.ticker;
        var m_nodes=$scope.my_nodes;
        var m_edges=$scope.my_edges;
        var new_nodes= [];
        var new_edges= [];
        var position=200;
        var child_num=0;
        var new_child;
        for (var i=0; i < m_nodes.length; i++) {
          if (m_nodes[i].label.toLowerCase() == test_value.toLowerCase() ) {
            if (!new_nodes.find(function(obj) {return obj.id==m_nodes[i].id })) {
              // console.log(m_nodes[i].label);  
              position+=5;  
              m_nodes[i].x=position;  
              new_nodes.push(m_nodes[i]);
            }
            // console.log(">>>"+m_nodes[i].label);  
            // console.log("<><><><><>"+m_edges.length);
            for (var x=0;x<m_edges.length;x++) {
              // console.log(m_edges[x].from + " " +m_nodes[i].id + " || " + m_edges[x].to + " " + m_nodes[i].id);
              if (m_edges[x].from==m_nodes[i].id || m_edges[x].to==m_nodes[i].id) {
                new_edges.push(m_edges[x]);
                if (m_edges[x].to!=m_nodes[i].id) {
                  if (!new_nodes.find(function(obj) { return obj.id==m_edges[x].to })) {
                    new_child=m_nodes.find( function(obj) { return obj.id==m_edges[x].to });
                    // console.log(new_child.label);       
                    new_child.x=position+child_num*2
                    new_child.y=position+child_num*2
                    new_nodes.push(new_child);
                  }
                }
                if (m_edges[x].from!=m_nodes[i].id) {
                  if (!new_nodes.find(function(obj){ return obj.id==m_edges[x].from })) {
                    new_child=m_nodes.find(function(obj){ return obj.id==m_edges[x].from });
                    // console.log(new_child.label); 
                    new_child.x=position+child_num*2
                    new_child.y=position+child_num*2
                    new_nodes.push(new_child);
                  }
                }
              }
            }
          }
        }

        if (test_value=="") {
          new_nodes=m_nodes;
          new_edges=$scope.my_edges;
        }

        $scope.data = {  
          nodes: new_nodes,
          edges: $scope.my_edges
        };
        $scope.network = new vis.Network($scope.container, $scope.data, {}); */
      }
    });

})();
