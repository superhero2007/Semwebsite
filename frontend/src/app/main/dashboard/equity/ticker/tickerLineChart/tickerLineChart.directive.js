/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.ticker')
      .directive('tickerLineChart', tickerLineChart);

  /** @ngInject */
  function tickerLineChart() {
    return {
      restrict: 'E',
      controller: 'TickerLineChartCtrl',
      templateUrl: 'app/main/dashboard/equity/ticker/tickerLineChart/tickerLineChart.html'
    };
  }
})();