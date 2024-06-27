from django.contrib import admin
from django.urls import path
from apps.cases.views import CaseViewSet

from rest_framework.routers import DefaultRouter
from django.conf.urls import include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView,SpectacularRedocView
router = DefaultRouter()

router.register(r"cases", CaseViewSet, basename="cases")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("data-model/", include("django_spaghetti.urls")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui')
]
