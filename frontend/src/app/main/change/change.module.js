/**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.change', [])
        .config(routeConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('change', {
                url: '/change',
                templateUrl: 'app/main/change/change.html',
                controller: 'ChangeController',
                title: 'Change'
            });
    }

    angular.module('BlurAdmin.main.change')
        .factory('ChangeService', ['$http', '$cookieStore', '$rootScope', function ($http, $cookieStore, $rootScope) {
            return {
                Change: function (username, oldPassword, newPassword, callback) {
                    $http.put('/api/user/change/', {username: username, oldPassword: oldPassword, newPassword: newPassword})
                        .success(function (response) {
                            callback(response);
                        });
                }
            };
        }]);

    angular.module('BlurAdmin.main.change')
        .controller('ChangeController', function ($rootScope, $scope, $location, ChangeService, LoginService) {

            $scope.change = function () {
                $scope.dataLoading = true;
                $scope.username = $rootScope.globals.currentUser.username;
                console.log($rootScope.globals);
                ChangeService.Change($scope.username, $scope.oldPassword, $scope.newPassword, function (response) {
                    if (response.success) {
                        console.log(response);
                        LoginService.SetCredentials($scope.username, $scope.newPassword);
                        $location.path('/dashboard/equity/latest');
                    } else {
                        $scope.error = response.message;
                        $scope.dataLoading = false;
                    }
                });
            };
        });
})();
