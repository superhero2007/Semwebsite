(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard')
      .directive('dashboardTable', dashboardTable);

  /** @ngInject */
  function dashboardTable() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/dashboard/tables/tables.html'
    };
  }
})();