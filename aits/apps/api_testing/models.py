from django.db import models

from apps.common.enums import ApiSchemaSourceType
from apps.common.models import TimeStampedModel
from apps.projects.models import Project


class ApiSchema(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="api_schemas",
    )
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, choices=ApiSchemaSourceType.choices)
    raw_content = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return self.name


class ApiEndpoint(TimeStampedModel):
    schema = models.ForeignKey(
        ApiSchema,
        on_delete=models.CASCADE,
        related_name="endpoints",
    )
    path = models.CharField(max_length=1024)
    method = models.CharField(max_length=16)
    summary = models.CharField(max_length=512, blank=True)
    request_schema = models.JSONField(default=dict, blank=True)
    response_schema = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["path", "method"]


class ApiTestCase(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="api_test_cases",
    )
    endpoint = models.ForeignKey(
        ApiEndpoint,
        on_delete=models.CASCADE,
        related_name="test_cases",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    request_data = models.JSONField(default=dict, blank=True)
    assertions = models.JSONField(default=dict, blank=True)
    generated_by_ai = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class ApiTestSuite(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="api_test_suites",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    test_cases = models.ManyToManyField(
        ApiTestCase,
        related_name="api_suites",
        blank=True,
    )

    def __str__(self) -> str:
        return self.name
