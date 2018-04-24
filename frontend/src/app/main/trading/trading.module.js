/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.trading', [
    'BlurAdmin.main.trading.dashboard',
    'BlurAdmin.main.trading.exposures',
  ]).config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('trading', {
        url: '/trading',
        template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
        abstract: true,
        title: 'Trading',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
  }

})();
