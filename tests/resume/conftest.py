import pytest

from job_applier.models.automation_settings import ResumeSettings
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


def localized(text: str) -> dict[str, str]:
    return {"pt": text, "en": f"{text} (en)"}


def bullet(text: str, tags: list[str]) -> dict:
    return {"text": localized(text), "tags": tags}


@pytest.fixture
def tailoring_resume(resume_data) -> Resume:
    resume_data["summaries"] = [
        {"id": "dev-junior", "tags": ["dev"], "text": localized("Resumo dev")},
        {"id": "devops-junior", "tags": ["devops"], "text": localized("Resumo devops")},
        {"id": "dev-devops", "tags": ["dev", "devops"], "text": localized("Resumo misto")},
    ]
    resume_data["experiences"] = [
        {
            "role": localized("Suporte em TI"),
            "company": "Empresa A",
            "period": {"start": "2025-04", "end": "2026-07"},
            "tags": ["suporte"],
            "bullets": [
                bullet("Atendimento a usuários", ["suporte"]),
                bullet("Automação de rotinas com Python", ["dev", "suporte", "python"]),
                bullet("Implantação de servidores com Docker", ["devops", "docker"]),
            ],
        },
        {
            "role": localized("Atendente"),
            "company": "Empresa B",
            "period": {"start": "2023-01", "end": "2024-01"},
            "tags": ["suporte"],
            "bullets": [
                bullet("Atendimento ao público", ["suporte"]),
                bullet("Organização de chamados", ["suporte"]),
            ],
        },
    ]
    resume_data["projects"] = [
        {"name": "infra-lab", "tags": ["devops"], "bullets": [bullet("Terraform na AWS", ["devops", "terraform"])]},
        {"name": "api-python", "tags": ["dev"], "bullets": [bullet("API em Python", ["dev", "python"])]},
    ]
    resume_data["skills"] = [
        {"term": "windows", "years": 10, "tags": ["suporte"]},
        {"term": "docker", "years": 1, "tags": ["devops"]},
        {"term": "python", "years": 2, "tags": ["dev"]},
        {"term": "react", "years": 1, "tags": ["dev"]},
        {"term": "terraform", "years": 1, "tags": ["devops"]},
    ]
    return Resume.model_validate(resume_data)


@pytest.fixture
def tailoring_glossary() -> Glossary:
    return Glossary.model_validate(
        {
            "terms": [
                {"id": "windows", "name": "Windows", "category": "operating_system"},
                {"id": "docker", "name": "Docker", "category": "devops"},
                {"id": "python", "name": "Python", "category": "language"},
                {"id": "react", "name": "React", "category": "frontend"},
                {"id": "terraform", "name": "Terraform", "category": "devops"},
            ]
        }
    )


@pytest.fixture
def resume_settings(settings_data) -> ResumeSettings:
    return ResumeSettings.model_validate(settings_data["resume"])
