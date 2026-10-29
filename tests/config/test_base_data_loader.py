import pytest

from job_applier.config.base_data_loader import BaseDataLoader, BaseDataPaths
from job_applier.config.json_model_loader import DataFileNotFoundError


class TestBaseDataLoader:
    def test_loads_versioned_config_with_example_personal_files(self, example_base_data):
        assert len(example_base_data.glossary.terms) >= 100

    def test_reports_missing_personal_file(self, tmp_path):
        with pytest.raises(DataFileNotFoundError, match="cv_base.json"):
            BaseDataLoader(BaseDataPaths.from_project_root(tmp_path)).load()
