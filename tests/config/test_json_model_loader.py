import pytest

from job_applier.config.json_model_loader import DataFileNotFoundError, InvalidDataFileError, JsonModelLoader
from job_applier.models.automation_settings import NumberRange


class TestJsonModelLoader:
    def test_loads_valid_file(self, tmp_path):
        path = tmp_path / "range.json"
        path.write_text('{"minimum": 1, "maximum": 2}', encoding="utf-8")

        assert JsonModelLoader().load(path, NumberRange) == NumberRange(minimum=1, maximum=2)

    def test_reports_missing_file(self, tmp_path):
        with pytest.raises(DataFileNotFoundError, match="Arquivo não encontrado"):
            JsonModelLoader().load(tmp_path / "inexistente.json", NumberRange)

    def test_reports_malformed_json(self, tmp_path):
        path = tmp_path / "range.json"
        path.write_text('{"minimum": 1,', encoding="utf-8")

        with pytest.raises(InvalidDataFileError, match="Arquivo inválido"):
            JsonModelLoader().load(path, NumberRange)

    def test_reports_data_that_breaks_the_model(self, tmp_path):
        path = tmp_path / "range.json"
        path.write_text('{"minimum": 5, "maximum": 1}', encoding="utf-8")

        with pytest.raises(InvalidDataFileError, match="maior que o máximo"):
            JsonModelLoader().load(path, NumberRange)
