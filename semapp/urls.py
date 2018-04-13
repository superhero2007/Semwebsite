from rest_framework import routers
from django.urls import include, path

router = routers.DefaultRouter()

urlpatterns = [
	path('api/', include(router.urls)),
]