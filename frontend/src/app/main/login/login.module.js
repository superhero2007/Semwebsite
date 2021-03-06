/**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.login', [])
        .config(routeConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('login', {
                url: '/login',
                templateUrl: 'app/main/login/login.html',
                controller: 'LoginController',
                title: 'Login'
            });
    }

    angular.module('BlurAdmin.main.login')
        .factory('LoginService', ['$http', '$cookieStore', '$rootScope', function ($http, $cookieStore, $rootScope) {
            return {
                Login: function (username, password, callback) {
                    $http.post('/api/user/', {username: username, password: password})
                        .success(function (response) {
                            callback(response);
                        });
                },
                SetCredentials: function (username, password) {
                    $rootScope.globals = {
                        currentUser: {
                            username: username,
                            password: password
                        }
                    };
                    $cookieStore.put('globals', $rootScope.globals);
                },
                ClearCredentials: function () {
                    $rootScope.globals = {};
                    $cookieStore.remove('globals');
                }
            };
        }]);

    angular.module('BlurAdmin.main.login')
        .controller('LoginController', function ($scope, $location, LoginService) {
            // reset login status
            LoginService.ClearCredentials();

            $scope.login = function () {
                $scope.dataLoading = true;
                LoginService.Login($scope.username, $scope.password, function (response) {
                    if (response.success) {
                        LoginService.SetCredentials($scope.username, $scope.password);
                        $location.path('/dashboard/equity/latest');
                    } else {
                        $scope.error = response.message;
                        $scope.dataLoading = false;
                    }
                });
            };
        });
})();
