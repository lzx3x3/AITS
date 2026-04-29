from django.db import models


class ProjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class MemberRole(models.TextChoices):
    OWNER = "owner", "Owner"
    EDITOR = "editor", "Editor"
    VIEWER = "viewer", "Viewer"


class ExecutionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class ExecutionType(models.TextChoices):
    API = "api", "API"
    WEB = "web", "Web"


class TriggerSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULER = "scheduler", "Scheduler"


class TargetType(models.TextChoices):
    CASE = "case", "Case"
    SUITE = "suite", "Suite"


class ApiSchemaSourceType(models.TextChoices):
    URL = "url", "URL"
    JSON = "json", "JSON"


class ReportType(models.TextChoices):
    ALLURE = "allure", "Allure"


class ScheduledJobType(models.TextChoices):
    API_SUITE = "api_suite", "API suite"
    WEB_SUITE = "web_suite", "Web suite"


class LlmProvider(models.TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    AZURE = "azure", "Azure"
    OTHER = "other", "Other"
