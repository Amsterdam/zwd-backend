from apps.cases.views import CaseViewSet
from apps.workflow.views import CaseWorkflowViewset, GenericCompletedTaskViewSet
from django.conf.urls import include
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"cases", CaseViewSet, basename="cases")
router.register(r"caseworkflow", CaseWorkflowViewset, basename="caseworkflow")
router.register(
    r"genericcompletedtask",
    GenericCompletedTaskViewSet,
    basename="genericcompletedtask",
)


def ok(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path("startup/", ok),
    path("", ok),  #
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("data-model/", include("django_spaghetti.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
