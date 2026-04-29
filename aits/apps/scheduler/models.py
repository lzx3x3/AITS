from django.db import models

from apps.common.enums import ScheduledJobType
from apps.common.models import TimeStampedModel
from apps.projects.models import Project


class ScheduledJob(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="scheduled_jobs",
    )
    name = models.CharField(max_length=255)
    job_type = models.CharField(max_length=32, choices=ScheduledJobType.choices)
    target_id = models.PositiveBigIntegerField()
    cron_expr = models.CharField(max_length=128)
    is_enabled = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
