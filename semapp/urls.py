from rest_framework import routers
from django.urls import include, path
from . import views

router = routers.DefaultRouter()

urlpatterns = [
	path('api/', include(router.urls)),
	path('api/Trading/Dashboard/', views.TradingView.as_view(), name='trading_dashboard'),
	path('api/Trading/Exposures/', views.TradingExposuresView.as_view(), name='trading_exposures'),
	path('api/Correlation/Daily/', views.NetworkView.as_view(), name='correlation_daily'),
	path('api/Correlation/View/', views.CorrelationView.as_view(), name='correlation_view'),
	path('api/Equity/Latest/', views.SignalsLatestView.as_view(), name='signal_latest'),
	path('api/Equity/SecInd/', views.SignalsSecIndView.as_view(), name='signal_secind'),
	path('api/Equity/Sector/', views.SignalsSectorTableView.as_view(), name='signal_sector'),
	path('api/Equity/Industry/', views.SignalsIndustryTableView.as_view(), name='signal_industry'),
	path('api/Equity/Ticker/', views.SignalsTickerView.as_view(), name='signal_ticker'),
	path('api/', include('authentication.urls')),
]