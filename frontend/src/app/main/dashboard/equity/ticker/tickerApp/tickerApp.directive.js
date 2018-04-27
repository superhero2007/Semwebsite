/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity.ticker')
      .directive('tickerApp', tickerApp);

  /** @ngInject */
  function tickerApp() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/dashboard/equity/ticker/tickerApp/tickerApp.html'
    };
  }
})();