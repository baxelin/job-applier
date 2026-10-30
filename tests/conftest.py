from pathlib import Path

import pytest

from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.models.base_data import BaseData

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def example_base_data() -> BaseData:
    """Configuração versionada (glossário real) com os dados pessoais fictícios de exemplo."""
    return BaseDataLoader(
        BaseDataPaths(
            resume=PROJECT_ROOT / "personal" / "cv_base.example.json",
            answer_book=PROJECT_ROOT / "personal" / "respostas.example.json",
            glossary=PROJECT_ROOT / "config" / "termos.json",
            settings=PROJECT_ROOT / "config" / "config.json",
        )
    ).load()


@pytest.fixture
def resume_data() -> dict:
    return {
        "contact": {
            "full_name": "Pessoa Teste",
            "email": "pessoa@example.com",
            "phone": "+55 11 90000-0000",
            "location": "São Paulo, SP",
            "linkedin_url": "https://www.linkedin.com/in/pessoa-teste",
            "github_url": "https://github.com/pessoa-teste",
        },
        "summaries": [
            {"id": "dev", "tags": ["dev"], "text": {"pt": "Resumo dev.", "en": "Dev summary."}},
            {"id": "devops", "tags": ["devops"], "text": {"pt": "Resumo devops.", "en": "DevOps summary."}},
        ],
        "experiences": [
            {
                "role": {"pt": "Desenvolvedora", "en": "Developer"},
                "company": "Empresa",
                "period": {"start": "2024-01", "end": "2025-06"},
                "tags": ["dev"],
                "bullets": [{"text": {"pt": "Fez algo útil.", "en": "Did something useful."}, "tags": ["dev"]}],
            }
        ],
        "skills": [{"term": "python", "years": 1, "tags": ["dev"]}],
    }


@pytest.fixture
def glossary_data() -> dict:
    return {
        "terms": [
            {"id": "python", "name": "Python", "category": "language", "synonyms": ["py"]},
            {"id": "docker", "name": "Docker", "category": "devops", "synonyms": []},
        ]
    }


@pytest.fixture
def answer_book_data() -> dict:
    return {
        "answers": [
            {"id": "inicio", "patterns": ["start date"], "answer": {"pt": "Imediata", "en": "Immediately"}},
            {"id": "pcd", "patterns": ["pcd"], "answer": None},
        ],
        "skill_years": {"patterns": ["anos de experiência com"], "default_years": 0},
        "salary": {
            "patterns": ["pretensão salarial"],
            "minimum": 2000,
            "default": 2400,
            "contractor_multiplier": 1.5,
        },
    }


@pytest.fixture
def settings_data() -> dict:
    return {
        "daily_application_limit": 10,
        "delay_between_actions_seconds": {"minimum": 1, "maximum": 3},
        "delay_between_applications_seconds": {"minimum": 30, "maximum": 60},
        "long_pause": {"every_applications": 5, "minutes": {"minimum": 5, "maximum": 10}},
        "filters": {
            "experience_levels": ["entry_level"],
            "workplace_types": ["remote"],
            "forbidden_title_words": ["sênior"],
        },
        "searches": [{"keywords": "Desenvolvedor Júnior", "location": "Brasil"}],
        "resume": {
            "weights": {"area_match": 3, "keyword_match": 2, "support_penalty": 5, "keyword_occurrence_cap": 3},
            "bullets_per_experience": {"minimum": 1, "maximum": 2},
            "bullets_per_project": {"minimum": 1, "maximum": 2},
            "max_projects": 1,
            "max_skills": 3,
            "summary_skill_count": 2,
        },
        "scan": {"max_pages_per_search": 2, "max_consecutive_extraction_errors": 2, "login_timeout_minutes": 5},
    }
