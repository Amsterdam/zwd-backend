from django.shortcuts import redirect
from apps.homeownerassociation.views import (
    DistrictViewset,
    HomeOwnerAssociationView,
    NeighborhoodViewset,
    WijkViewset,
)
from apps.address.views import AddressViewSet
from apps.cases.views import CaseCloseViewSet, CaseStatusViewset, CaseViewSet
from apps.workflow.views import (
    CaseUserTaskViewSet,
    GenericCompletedTaskViewSet,
    BpmnViewSet,
)
from apps.advisor.views import AdvisorViewset
from django.conf.urls import include
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView


router = DefaultRouter()
router.register(r"cases", CaseViewSet, basename="cases")
router.register(r"generic-tasks", GenericCompletedTaskViewSet, basename="generictasks")
router.register(r"tasks", CaseUserTaskViewSet, basename="tasks")
router.register(r"bpmn-models", BpmnViewSet, basename="bpmn-models")
router.register(r"address", AddressViewSet, basename="address")
router.register(
    r"homeowner-association", HomeOwnerAssociationView, basename="homeownerassociation"
)
router.register(r"districts", DistrictViewset, basename="district")
router.register(r"wijken", WijkViewset, basename="wijk")
router.register(r"neighborhoods", NeighborhoodViewset, basename="neighborhoods")
router.register(r"case-statuses", CaseStatusViewset, basename="case-status")
router.register(r"case-close", CaseCloseViewSet, basename="case-close")
router.register(r"advisors", AdvisorViewset, basename="advisors")


@login_required
def admin_redirect(request):
    return redirect("/admin")


def ok(request):
    return HttpResponse("OK", status=200)


admin.site.site_header = "Zaken Woningkwaliteit en Duurzaamheid"
admin.site.site_title = "Administration"
admin.site.index_title = "ZWD"


urlpatterns = [
    path("startup/", ok),
    path("", ok),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("admin/login/", admin_redirect),
    path("admin/", admin.site.urls),
    path("api/v1/", include(router.urls)),
    path("data-model/", include("django_spaghetti.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        ".well-known/security.txt",
        RedirectView.as_view(url="https://www.amsterdam.nl/.well-known/security.txt"),
    ),
]
