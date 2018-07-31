/**
 * @author max.apollo
 * created on 04.20.2018
 */
(function () {
    'use strict';

    angular.module('BlurAdmin.main.dashboard.factor', [])
        .config(routeConfig).config(amChartConfig);

    /** @ngInject */
    function routeConfig($stateProvider) {
        $stateProvider
            .state('dashboard.factor', {
                url: '/factor',
                templateUrl: 'app/main/dashboard/factor/factor.html',
                controller: 'FactorController',
                title: 'Factor Returns',
                sidebarMeta: {
                    icon: '',
                    order: 200,
                },
            });
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

    angular.module('BlurAdmin.main.dashboard.factor')
        .factory('FactorService', function ($http) {
            return {
                getData: function (start_date, end_date, selected_factors) {
                    return $http.post('api/Factor/', {
                        start_date: start_date,
                        end_date: end_date,
                        selected_factors: selected_factors
                    }).then(function (result) {
                        return result.data
                    });
                }
            }
        });

    angular.module('BlurAdmin.main.dashboard.factor')
        .controller('FactorController', function ($scope, $timeout, FactorService, baConfig) {
            var layoutColors = baConfig.colors;
            $scope.filter = {
                date: {
                    startDate: moment("2018-01-01"),
                    endDate: moment()
                },
                selected_factors: ['Style: Growth', 'Style: Value'],
                include_it_data: false
            };
            $scope.multipleItem = {
                selected: ['Style: Growth', 'Style: Value']
            };
            $scope.showGraph = function () {
                $scope.filter.selected_factors = $scope.multipleItem.selected;
                FactorService.getData($scope.filter.date.startDate, $scope.filter.date.endDate, $scope.filter.selected_factors).then(function (data) {
                    $scope.data = data.data;
                    $scope.multipleSelectItems = data.all_factors;
                    $scope.chartData = JSON.parse(JSON.stringify($scope.data));
                    for (var i = 1; i < $scope.chartData.length; i++) {
                        for (var j = 0; j < $scope.filter.selected_factors.length; j++) {
                            $scope.chartData[i][$scope.filter.selected_factors[j]] = $scope.chartData[i][$scope.filter.selected_factors[j]] * 100 + $scope.chartData[i-1][$scope.filter.selected_factors[j]];
                        }
                    }
                    $scope.graphs = [];
                    for (i = 0; i < $scope.filter.selected_factors.length; i++) {
                        $scope.graphs.push(
                            {
                                "id": "g" + (i + 1),
                                "valueAxis": "v1",
                                color: layoutColors.defaultText,
                                "hideBulletsCount": 50,
                                "lineThickness": 2,
                                "type": "smoothedLine",
                                "title": $scope.filter.selected_factors[i],
                                "useLineColorForBulletBorder": true,
                                "valueField": $scope.filter.selected_factors[i],
                                "balloonText": "[[title]]<br/><b style='font-size: 130%'>[[value]]</b>"
                            })
                    }

                    if ($scope.multipleItem.selected.length === 2 && $scope.filter.include_it_data) {
                        for (i = 0; i < $scope.chartData.length; i++) {
                            $scope.chartData[i]["plot"] = ($scope.chartData[i][$scope.filter.selected_factors[0]] + 1) / ($scope.chartData[i][$scope.filter.selected_factors[1]] + 1);
                        }
                        $scope.graphs.push(
                            {
                                "id": "plot",
                                "valueAxis": "v2",
                                color: layoutColors.defaultText,
                                "hideBulletsCount": 50,
                                "lineThickness": 2,
                                "type": "smoothedLine",
                                "title": "Plot",
                                "useLineColorForBulletBorder": true,
                                "valueField": "plot",
                                "balloonText": "[[title]]<br/><b style='font-size: 130%'>[[value]]</b>"
                            })
                    }

                    var chart = AmCharts.makeChart("myFactor", {
                        "type": "serial",
                        "theme": "none",
                        "color": layoutColors.defaultText,
                        "dataDateFormat": "YYYY-MM-DD",
                        "precision": 5,
                        "valueAxes": [{
                            color: layoutColors.defaultText,
                            axisColor: layoutColors.defaultText,
                            gridColor: layoutColors.defaultText,
                            "id": "v1",
                            "position": "right",
                            "autoGridCount": false
                        },
                        {
                            color: layoutColors.defaultText,
                            axisColor: layoutColors.defaultText,
                            gridColor: layoutColors.defaultText,
                            "id": "v2",
                            "position": "left",
                            "autoGridCount": false
                        }],
                        "graphs": $scope.graphs,
                        "chartScrollbar": {
                            "graph": "g3",
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
                        "dataProvider": $scope.chartData
                    });
                    $scope.flag = false;
                    chart.addListener("zoomed", function(e) {
                        if ($scope.flag == true) {
                            return;
                        }
                        var startIndex = e.chart.startIndex, endIndex = e.chart.endIndex;
                        $scope.chartData = JSON.parse(JSON.stringify($scope.data));
                        for (var i = startIndex + 1; i <= endIndex; i++) {
                            for (var j = 0; j < $scope.filter.selected_factors.length; j++) {
                                $scope.chartData[i][$scope.filter.selected_factors[j]] = $scope.chartData[i][$scope.filter.selected_factors[j]] * 100 + $scope.chartData[i-1][$scope.filter.selected_factors[j]];
                            }
                        }
                        chart.dataProvider = $scope.chartData;
                        $scope.flag = true;
                        chart.validateData();
                        chart.zoomToIndexes(startIndex, endIndex - 1);
                        $scope.flag = false;
                    });
                });
            };
            $scope.showGraph();
            $scope.dateChange = function (ev, picker) {
                $scope.showGraph();
            };
            $scope.onChange = function (data, value) {
                $scope.filter.include_it_data = value;
                $scope.showGraph();
            };
        });

})();
