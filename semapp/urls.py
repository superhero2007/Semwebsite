from rest_framework import routers
from django.urls import include, path
from . import views

router = routers.DefaultRouter()

urlpatterns = [
	path('api/', include(router.urls)),
	path('api/Trading/Dashboard/', views.TradingView.as_view(), name='trading_dashboard'),
	path('api/Trading/Exposures/', views.TradingExposuresView.as_view(), name='trading_exposures'),
	path('api/Network/', views.NetworkView.as_view(), name='network'),
	path('api/Equity/Latest/', views.SignalsLatestView.as_view(), name='signal_latest'),
	path('api/Equity/Ticker/<str:ticker>/', views.SignalsTickerView.as_view(), name='signal_ticker'),
	path('api/', include('authentication.urls')),
]