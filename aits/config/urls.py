"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from apps.api_testing.ui_views import ApiTestingWorkbenchView


def api_root(_request):
    return JsonResponse({"message": "AITS API v1"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ui/api-testing/", ApiTestingWorkbenchView.as_view(), name="api-testing-workbench"),
    path("api/v1/", api_root, name="api-root"),
    path("api/v1/common/", include("apps.common.urls")),
    path("api/v1/projects/", include("apps.projects.urls")),
    path("api/v1/environments/", include("apps.projects.environment_urls")),
    path("api/v1/project-members/", include("apps.projects.member_urls")),
    path("api/v1/api-testing/", include("apps.api_testing.urls")),
    path("api/v1/web-testing/", include("apps.web_testing.urls")),
    path("api/v1/ai/", include("apps.ai_core.urls")),
    path("api/v1/ai-core/", include("apps.ai_core.urls")),
    path("api/v1/executions/", include("apps.executions.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/scheduler/", include("apps.scheduler.urls")),
]
