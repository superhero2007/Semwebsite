/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.latest')
      .directive('latestTable', latestTable);

  /** @ngInject */
  function latestTable() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/dashboard/equity/latest/tables/tables.html'
    };
  }
})();