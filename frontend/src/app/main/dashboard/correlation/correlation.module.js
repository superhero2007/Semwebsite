/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
  'use strict';

  angular.module('BlurAdmin.main.dashboard.correlation', [
    'BlurAdmin.main.dashboard.correlation.daily',
    'BlurAdmin.main.dashboard.correlation.table',
    'BlurAdmin.main.dashboard.correlation.network'
  ])
    .config(routeConfig);

  /** @ngInject */
  function routeConfig($stateProvider) {
    $stateProvider
      .state('dashboard.correlation', {
        url: '/correlation',
        template : '<ui-view autoscroll="true" autoscroll-body-top></ui-view>',
        abstract: true,
        title: 'Correlation',
        sidebarMeta: {
          icon: '',
          order: 100,
        },
      })
  }

})();
