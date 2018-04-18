from rest_framework import routers
from django.urls import include, path
from . import views

router = routers.DefaultRouter()

urlpatterns = [
	path('api/', include(router.urls)),
	path('api/Trading/Dashboard/', views.TradingView.as_view(), name='trading_dashboard')
]