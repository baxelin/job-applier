import logging
from datetime import date

from job_applier.execution_log import ExecutionLog


def test_writes_the_messages_to_a_file_of_the_day(tmp_path):
    log = ExecutionLog(tmp_path / "logs", today=lambda: date(2026, 11, 19))

    path = log.configure()
    logging.getLogger("job_applier.teste").info("Abrindo vaga 123.")
    log.close()

    assert path == tmp_path / "logs" / "2026-11-19.log"
    assert "Abrindo vaga 123." in path.read_text(encoding="utf-8")


def test_configuring_again_does_not_duplicate_lines(tmp_path):
    log = ExecutionLog(tmp_path / "logs", today=lambda: date(2026, 11, 19))

    log.configure()
    path = log.configure()
    logging.getLogger("job_applier.teste").info("Uma vez só.")
    log.close()

    assert path.read_text(encoding="utf-8").count("Uma vez só.") == 1
