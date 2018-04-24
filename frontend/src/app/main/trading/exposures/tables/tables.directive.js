/**
 * @author max.apollo
 * created on 04.23.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading.exposures')
      .directive('exposuresTable', exposuresTable);

  /** @ngInject */
  function exposuresTable() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/trading/exposures/tables/tables.html'
    };
  }
})();