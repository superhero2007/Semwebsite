/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading')
      .directive('tradingTable', tradingTable);

  /** @ngInject */
  function tradingTable() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/trading/tables/tables.html'
    };
  }
})();