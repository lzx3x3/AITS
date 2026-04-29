from django.db import models

from apps.common.enums import ReportType
from apps.common.models import TimeStampedModel
from apps.executions.models import TestExecution


class TestReport(TimeStampedModel):
    execution = models.OneToOneField(
        TestExecution,
        on_delete=models.CASCADE,
        related_name="report",
    )
    report_type = models.CharField(
        max_length=32,
        choices=ReportType.choices,
        default=ReportType.ALLURE,
    )
    report_path = models.CharField(max_length=1024, blank=True)
    report_url = models.CharField(max_length=1024, blank=True)
    metrics = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"report:{self.execution_id}"
