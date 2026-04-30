from django.core.exceptions import ObjectDoesNotExist

from apps.ai_core.models import PromptTemplate


class PromptNotFoundError(ObjectDoesNotExist):
    """Raised when prompt template cannot be found."""


class PromptManager:
    @staticmethod
    def get_prompt(scene: str, version: int | None = None) -> str:
        queryset = PromptTemplate.objects.filter(scene=scene)
        if version is not None:
            template = queryset.filter(version=version).first()
            if template is None:
                raise PromptNotFoundError(
                    f"Prompt template not found for scene='{scene}', version={version}."
                )
            return template.template_text

        template = queryset.filter(is_default=True).order_by("-updated_at", "-id").first()
        if template is None:
            raise PromptNotFoundError(
                f"Default prompt template not found for scene='{scene}'."
            )
        return template.template_text
