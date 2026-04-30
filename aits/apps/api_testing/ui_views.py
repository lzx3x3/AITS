from django.views.generic import TemplateView


class ApiTestingWorkbenchView(TemplateView):
    template_name = "api_testing/workbench.html"
