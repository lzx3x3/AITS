from django.db import models

from apps.common.enums import ExecutionStatus, ExecutionType, TargetType, TriggerSource
from apps.common.models import TimeStampedModel
from apps.projects.models import Project


class TestExecution(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="test_executions",
    )
    execution_type = models.CharField(max_length=16, choices=ExecutionType.choices)
    target_type = models.CharField(max_length=16, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=32,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING,
    )
    trigger_source = models.CharField(
        max_length=32,
        choices=TriggerSource.choices,
        default=TriggerSource.MANUAL,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    log_path = models.CharField(max_length=1024, blank=True)
    artifact_path = models.CharField(max_length=1024, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ExecutionStepLog(models.Model):
    execution = models.ForeignKey(
        TestExecution,
        on_delete=models.CASCADE,
        related_name="step_logs",
    )
    step_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.PENDING,
    )
    message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "id"]
