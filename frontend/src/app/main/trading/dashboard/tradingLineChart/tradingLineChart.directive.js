/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading.dashboard')
      .directive('tradingLineChart', tradingLineChart);

  /** @ngInject */
  function tradingLineChart() {
    return {
      restrict: 'E',
      controller: 'TradingLineChartCtrl',
      templateUrl: 'app/main/trading/dashboard/tradingLineChart/tradingLineChart.html'
    };
  }
})();