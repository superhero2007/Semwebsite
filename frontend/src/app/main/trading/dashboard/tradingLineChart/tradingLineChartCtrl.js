/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading.dashboard').config(chartJsConfig)
    .controller('TradingLineChartCtrl', TradingLineChartCtrl);

  function createDate(time_t) {
    var date = new Date(time_t * 1000);
    return date;
  }

  /** @ngInject */
  function TradingLineChartCtrl($scope, DashboardService) {
    DashboardService.getData().then(function(data) {
      var chartDataStrategy = [];
      var chartDataBenchmark = [];

      for (var x=0; x < data.chart_data_strategy.length; x++) {
        chartDataStrategy[x] = {
          x: createDate(data.chart_data_strategy[x][0]),
          y: data.chart_data_strategy[x][1]
        };
      }

      for (var x=0; x < data.chart_data_benchmark.length; x++) {
        chartDataBenchmark[x] = {
          x: createDate(data.chart_data_benchmark[x][0]),
          y: data.chart_data_benchmark[x][1]
        };
      }

      $scope.data = [
        chartDataStrategy,
        chartDataBenchmark
      ];

      $scope.options = {
        scales: {
          xAxes: [{
            type: 'time',
            time: {
              displayFormats: {
                day: 'MMM D',
                week: 'MMM D'
              }
            }
          }]
        }
      };

      $scope.series = ["Strategy", data.benchmark_name];
    })
  }

  function chartJsConfig(ChartJsProvider, baConfigProvider) {
    var layoutColors = baConfigProvider.colors;
    // Configure all charts
    ChartJsProvider.setOptions({
      chartColors: [
        layoutColors.primary, layoutColors.danger, layoutColors.warning, layoutColors.success, layoutColors.info, layoutColors.default, layoutColors.primaryDark, layoutColors.successDark, layoutColors.warningLight, layoutColors.successLight, layoutColors.primaryLight],
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 2500
      },
      scale: {
        gridLines: {
          color: layoutColors.border
        },
        scaleLabel: {
          fontColor: layoutColors.defaultText
        },
        ticks: {
          fontColor: layoutColors.defaultText,
          showLabelBackdrop: false
        }
      }
    });

    // Configure all line charts
    ChartJsProvider.setOptions('Line', {
      datasetFill: false
    });
  }

})();