/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.sector')
      .directive('sectorTable', sectorTable);

  /** @ngInject */
  function sectorTable() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/dashboard/equity/sector/tables/tables.html'
    };
  }
})();