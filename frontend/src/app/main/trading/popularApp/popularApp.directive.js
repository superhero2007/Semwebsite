/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading')
      .directive('popularApp', popularApp);

  /** @ngInject */
  function popularApp() {
    return {
      restrict: 'E',
      templateUrl: 'app/main/trading/popularApp/popularApp.html'
    };
  }
})();