/**
 * @author max.apollo
 * created on 4/23/18
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.equity.ticker', [])
        .config(routeConfig).config(amChartConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('dashboard.equity.ticker', {
                url: '/ticker',
                templateUrl: 'app/main/dashboard/equity/ticker/ticker.html',
                controller: 'TickerController',
                title: 'Ticker Signal History',
                sidebarMeta: {
                    icon: '',
                    order: 200,
                },
                params: {
                    obj: null
                }
            })
    }

    function amChartConfig(baConfigProvider) {
        var layoutColors = baConfigProvider.colors;
        AmCharts.themes.blur = {

            themeName: "blur",

            AmChart: {
                color: layoutColors.defaultText,
                backgroundColor: "#FFFFFF"
            },

            AmCoordinateChart: {
                colors: [layoutColors.primary, layoutColors.danger, layoutColors.warning, layoutColors.success, layoutColors.info, layoutColors.primaryDark, layoutColors.warningLight, layoutColors.successDark, layoutColors.successLight, layoutColors.primaryLight, layoutColors.warningDark]
            },

            AmStockChart: {
                colors: [layoutColors.primary, layoutColors.danger, layoutColors.warning, layoutColors.success, layoutColors.info, layoutColors.primaryDark, layoutColors.warningLight, layoutColors.successDark, layoutColors.successLight, layoutColors.primaryLight, layoutColors.warningDark]
            },

            AmSlicedChart: {
                colors: [layoutColors.primary, layoutColors.danger, layoutColors.warning, layoutColors.success, layoutColors.info, layoutColors.primaryDark, layoutColors.warningLight, layoutColors.successDark, layoutColors.successLight, layoutColors.primaryLight, layoutColors.warningDark],
                labelTickColor: "#FFFFFF",
                labelTickAlpha: 0.3
            },

            AmRectangularChart: {
                zoomOutButtonColor: '#FFFFFF',
                zoomOutButtonRollOverAlpha: 0.15,
                zoomOutButtonImage: "lens.png"
            },

            AxisBase: {
                axisColor: "#FFFFFF",
                axisAlpha: 0.3,
                gridAlpha: 0.1,
                gridColor: "#FFFFFF"
            },

            ChartScrollbar: {
                backgroundColor: "#FFFFFF",
                backgroundAlpha: 0.12,
                graphFillAlpha: 0.5,
                graphLineAlpha: 0,
                selectedBackgroundColor: "#FFFFFF",
                selectedBackgroundAlpha: 0.4,
                gridAlpha: 0.15
            },

            ChartCursor: {
                cursorColor: layoutColors.primary,
                color: "#FFFFFF",
                cursorAlpha: 0.5
            },

            AmLegend: {
                color: "#FFFFFF"
            },

            AmGraph: {
                lineAlpha: 0.9
            },
            GaugeArrow: {
                color: "#FFFFFF",
                alpha: 0.8,
                nailAlpha: 0,
                innerRadius: "40%",
                nailRadius: 15,
                startWidth: 15,
                borderAlpha: 0.8,
                nailBorderAlpha: 0
            },

            GaugeAxis: {
                tickColor: "#FFFFFF",
                tickAlpha: 1,
                tickLength: 15,
                minorTickLength: 8,
                axisThickness: 3,
                axisColor: '#FFFFFF',
                axisAlpha: 1,
                bandAlpha: 0.8
            },

            TrendLine: {
                lineColor: layoutColors.danger,
                lineAlpha: 0.8
            },

            // ammap
            AreasSettings: {
                alpha: 0.8,
                color: layoutColors.info,
                colorSolid: layoutColors.primaryDark,
                unlistedAreasAlpha: 0.4,
                unlistedAreasColor: "#FFFFFF",
                outlineColor: "#FFFFFF",
                outlineAlpha: 0.5,
                outlineThickness: 0.5,
                rollOverColor: layoutColors.primary,
                rollOverOutlineColor: "#FFFFFF",
                selectedOutlineColor: "#FFFFFF",
                selectedColor: "#f15135",
                unlistedAreasOutlineColor: "#FFFFFF",
                unlistedAreasOutlineAlpha: 0.5
            },

            LinesSettings: {
                color: "#FFFFFF",
                alpha: 0.8
            },

            ImagesSettings: {
                alpha: 0.8,
                labelColor: "#FFFFFF",
                color: "#FFFFFF",
                labelRollOverColor: layoutColors.primaryDark
            },

            ZoomControl: {
                buttonFillAlpha: 0.8,
                buttonIconColor: layoutColors.defaultText,
                buttonRollOverColor: layoutColors.danger,
                buttonFillColor: layoutColors.primaryDark,
                buttonBorderColor: layoutColors.primaryDark,
                buttonBorderAlpha: 0,
                buttonCornerRadius: 0,
                gridColor: "#FFFFFF",
                gridBackgroundColor: "#FFFFFF",
                buttonIconAlpha: 0.6,
                gridAlpha: 0.6,
                buttonSize: 20
            },

            SmallMap: {
                mapColor: "#000000",
                rectangleColor: layoutColors.danger,
                backgroundColor: "#FFFFFF",
                backgroundAlpha: 0.7,
                borderThickness: 1,
                borderAlpha: 0.8
            },

            // the defaults below are set using CSS syntax, you can use any existing css property
            // if you don't use Stock chart, you can delete lines below
            PeriodSelector: {
                color: "#FFFFFF"
            },

            PeriodButton: {
                color: "#FFFFFF",
                background: "transparent",
                opacity: 0.7,
                border: "1px solid rgba(0, 0, 0, .3)",
                MozBorderRadius: "5px",
                borderRadius: "5px",
                margin: "1px",
                outline: "none",
                boxSizing: "border-box"
            },

            PeriodButtonSelected: {
                color: "#FFFFFF",
                backgroundColor: "#b9cdf5",
                border: "1px solid rgba(0, 0, 0, .3)",
                MozBorderRadius: "5px",
                borderRadius: "5px",
                margin: "1px",
                outline: "none",
                opacity: 1,
                boxSizing: "border-box"
            },

            PeriodInputField: {
                color: "#FFFFFF",
                background: "transparent",
                border: "1px solid rgba(0, 0, 0, .3)",
                outline: "none"
            },

            DataSetSelector: {
                color: "#FFFFFF",
                selectedBackgroundColor: "#b9cdf5",
                rollOverBackgroundColor: "#a8b0e4"
            },

            DataSetCompareList: {
                color: "#FFFFFF",
                lineHeight: "100%",
                boxSizing: "initial",
                webkitBoxSizing: "initial",
                border: "1px solid rgba(0, 0, 0, .3)"
            },

            DataSetSelect: {
                border: "1px solid rgba(0, 0, 0, .3)",
                outline: "none"
            }

        };
    }

    angular.module('BlurAdmin.main.dashboard.equity.ticker')
        .factory('TickerService', function ($http) {
            return {
                getData: function (ticker) {
                    return $http.post('/api/Equity/Ticker/', {ticker: ticker}).then(function (result) {
                        return result.data
                    });
                }
            };
        });

    angular.module('BlurAdmin.main.dashboard.equity.ticker')
        .controller('TickerController', function ($scope, $stateParams, TickerService, baConfig) {
            var layoutColors = baConfig.colors;
            $scope.filterParameter = $stateParams.obj;
            $scope.filter = {
                ticker: ''
            };
            $scope.showChart = function () {
                TickerService.getData($scope.filter.ticker).then(function (data) {
                    $scope.tickerData = data.signal_data;
                    $scope.info = {
                        cik: data['CIK'],
                        industry: data['Industry'],
                        market_cap: data['Market Cap'],
                        name: data['Name'],
                        sector: data['Sector'],
                        ticker: data['ticker']
                    };
                    if (!$scope.tickerData) {
                        return
                    }
                    for (var i = 0; i < $scope.tickerData.length; i++) {
                        $scope.tickerData[i].max = 1;
                        $scope.tickerData[i].long = 0.55;
                        $scope.tickerData[i].short = 0.45;
                        $scope.tickerData[i].min = 0;
                    }

                    var chart = AmCharts.makeChart("tickerChart", {
                        "type": "serial",
                        "theme": "none",
                        "color": layoutColors.defaultText,
                        "dataDateFormat": "YYYY-MM-DD",
                        "precision": 2,
                        "valueAxes": [{
                            color: layoutColors.defaultText,
                            axisColor: layoutColors.defaultText,
                            gridColor: layoutColors.defaultText,
                            "id": "v1",
                            "position": "left",
                            "autoGridCount": false,
                            "minimum": 0
                        }, {
                            color: layoutColors.defaultText,
                            axisColor: layoutColors.defaultText,
                            gridColor: layoutColors.defaultText,
                            "id": "v2",
                            "gridAlpha": 0,
                            "position": "right",
                            "autoGridCount": false,
                            "minimum": 0,
                            "maximum": 1
                        }],
                        "graphs": [
                            {
                                "id": "g1",
                                "valueAxis": "v1",
                                color: layoutColors.defaultText,
                                "hideBulletsCount": 50,
                                "lineThickness": 2,
                                "lineColor": layoutColors.success,
                                "type": "smoothedLine",
                                "title": $scope.filter.ticker.toUpperCase(),
                                "useLineColorForBulletBorder": true,
                                "valueField": "adj_close",
                                "balloonText": "[[title]]<br/><b style='font-size: 130%'>[[value]]</b>"
                            },
                            {
                                "id": "g2",
                                "valueAxis": "v2",
                                color: layoutColors.defaultText,
                                "hideBulletsCount": 50,
                                "lineThickness": 2,
                                "lineColor": layoutColors.info,
                                "type": "smoothedLine",
                                "title": "Signal Strength",
                                "useLineColorForBulletBorder": true,
                                "valueField": "SignalConfidence",
                                "balloonText": "[[title]]<br/><b style='font-size: 130%'>[[value]]</b>"
                            },
                            {
                                "id": "long",
                                "valueAxis": "v2",
                                "lineAlpha": 0,
                                "valueField": "long",
                                "title": "Long",
                                "fillAphas": 0,
                                "showBalloon": false
                            },
                            {
                                "id": "g3",
                                "valueAxis": "v2",
                                "fillAlphas": 0.3,
                                "lineAlpha": 0,
                                "valueField": "max",
                                "fillToGraph": "long",
                                "fillColors": layoutColors.success,
                                "legendColor": layoutColors.success,
                                "visibleInLegend": false,
                                "showBalloon": false
                            },
                            {
                                "id": "min",
                                "valueAxis": "v2",
                                "lineAlpha": 0,
                                "valueField": "min",
                                "fillAphas": 0,
                                "showBalloon": false,
                                "visibleInLegend": false
                            },
                            {
                                "id": "g4",
                                "valueAxis": "v2",
                                "fillAlphas": 0.3,
                                "lineAlpha": 0,
                                "valueField": "short",
                                "fillToGraph": "min",
                                "title": "Short",
                                "legendColor": layoutColors.danger,
                                "fillColors": layoutColors.danger,
                                "showBalloon": false
                            }
                        ],
                        "chartScrollbar": {
                            "graph": "g1",
                            "oppositeAxis": false,
                            "offset": 30,
                            gridAlpha: 0,
                            color: layoutColors.defaultText,
                            scrollbarHeight: 50,
                            backgroundAlpha: 0,
                            selectedBackgroundAlpha: 0.05,
                            selectedBackgroundColor: layoutColors.defaultText,
                            graphFillAlpha: 0,
                            autoGridCount: true,
                            selectedGraphFillAlpha: 0,
                            graphLineAlpha: 0.2,
                            selectedGraphLineColor: layoutColors.defaultText,
                            selectedGraphLineAlpha: 1
                        },
                        "chartCursor": {
                            "pan": true,
                            "cursorColor": layoutColors.danger,
                            "valueLineEnabled": true,
                            "valueLineBalloonEnabled": true,
                            "cursorAlpha": 0,
                            "valueLineAlpha": 0.2
                        },
                        "categoryField": "data_date",
                        "categoryAxis": {
                            "axisColor": layoutColors.defaultText,
                            "color": layoutColors.defaultText,
                            "gridColor": layoutColors.defaultText,
                            "parseDates": true,
                            "dashLength": 1,
                            "minorGridEnabled": true
                        },
                        "legend": {
                            "useGraphSettings": true,
                            "position": "top",
                            "color": layoutColors.defaultText,
                            "valueText": ""
                        },
                        "balloon": {
                            "borderThickness": 1,
                            "shadowAlpha": 0
                        },
                        "export": {
                            "enabled": true
                        },
                        "dataProvider": $scope.tickerData
                    });
                })
            };
            $scope.tickerData = [];
            if ($scope.filterParameter) {
                $scope.filter.ticker = $scope.filterParameter;
                $scope.showChart();
            }
            $scope.filter_ticker = function () {
                if ($scope.filter.ticker !== '') {
                    $scope.showChart();
                } else {
                    $scope.tickerData = [];
                }
            };
        });
})();
