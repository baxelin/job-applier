from pathlib import Path

import pytest

from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.config.json_model_loader import DataFileNotFoundError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestBaseDataLoader:
    def test_loads_versioned_config_with_example_personal_files(self):
        paths = BaseDataPaths(
            resume=PROJECT_ROOT / "personal" / "cv_base.example.json",
            answer_book=PROJECT_ROOT / "personal" / "respostas.example.json",
            glossary=PROJECT_ROOT / "config" / "termos.json",
            settings=PROJECT_ROOT / "config" / "config.json",
        )

        base_data = BaseDataLoader(paths).load()

        assert len(base_data.glossary.terms) >= 100

    def test_reports_missing_personal_file(self, tmp_path):
        with pytest.raises(DataFileNotFoundError, match="cv_base.json"):
            BaseDataLoader(BaseDataPaths.from_project_root(tmp_path)).load()
