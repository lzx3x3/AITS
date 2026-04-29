from django.conf import settings
from django.db import models

from apps.common.enums import MemberRole, ProjectStatus
from apps.common.models import TimeStampedModel


class Project(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Environment(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="environments",
    )
    name = models.CharField(max_length=128)
    base_url = models.URLField(max_length=512)
    variables = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.name}"


class ProjectMember(TimeStampedModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=MemberRole.choices,
        default=MemberRole.VIEWER,
    )

    class Meta:
        unique_together = [("project", "user")]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.user_id}"
