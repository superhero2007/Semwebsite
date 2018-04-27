/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.equity', [
    'BlurAdmin.main.dashboard.equity.latest',
    'BlurAdmin.main.dashboard.equity.sector',
    'BlurAdmin.main.dashboard.equity.ticker'
  ])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.equity', {
        url: '/equity',
        template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
        abstract: true,
        title: 'Equity Signals',
        sidebarMeta: {
          icon: '',
          order: 0,
        },
      })
  }

})();
