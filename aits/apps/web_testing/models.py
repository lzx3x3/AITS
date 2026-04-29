from django.db import models

from apps.common.models import TimeStampedModel
from apps.projects.models import Project


class WebTestCase(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="web_test_cases",
    )
    title = models.CharField(max_length=255)
    requirement_text = models.TextField(blank=True)
    playwright_script = models.TextField(blank=True)
    generated_by_ai = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class WebTestSuite(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="web_test_suites",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    test_cases = models.ManyToManyField(
        WebTestCase,
        related_name="web_suites",
        blank=True,
    )

    def __str__(self) -> str:
        return self.name
