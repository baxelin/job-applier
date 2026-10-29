import os
from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from job_applier.models.job_application import ApplicationStatus, JobApplication, UnknownQuestion


class SpreadsheetLockedError(Exception):
    """A planilha não pôde ser gravada (normalmente porque está aberta no Excel)."""


class ExcelReportWriter:
    """Gera a planilha data/candidaturas.xlsx a partir do banco, com as abas Vagas e Perguntas.

    A planilha é só um relatório: é recriada inteira a cada execução, então se uma gravação
    falhar os dados continuam no banco e a próxima execução a atualiza.
    """

    _APPLICATION_HEADERS = (
        ("Data", 17), ("Empresa", 24), ("Vaga", 42), ("Local", 24), ("Status", 20), ("Aderência", 11),
        ("Foco", 14), ("Idioma", 8), ("Vaga de suporte", 15), ("Tem", 50), ("Falta", 40), ("CV", 50),
        ("Link da vaga", 14), ("Atualizado em", 17),
    )
    _QUESTION_HEADERS = (("Pergunta", 70), ("Ocorrências", 12), ("Última vaga", 50), ("Primeira vez", 17),
                         ("Última vez", 17))
    _STATUS_LABELS = {
        ApplicationStatus.CV_GENERATED: "CV gerado",
        ApplicationStatus.APPLIED: "Candidatura enviada",
        ApplicationStatus.SKIPPED: "Ignorada",
        ApplicationStatus.FAILED: "Erro",
    }
    _DATE_FORMAT = "dd/mm/yyyy hh:mm"
    _HEADER_FONT = Font(bold=True, color="FFFFFF")
    _HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
    _LINK_FONT = Font(color="1155CC", underline="single")

    def __init__(self, path: Path, project_root: Path) -> None:
        self._path = path
        self._project_root = project_root

    def write(self, applications: Sequence[JobApplication], questions: Sequence[UnknownQuestion]) -> None:
        workbook = Workbook()
        applications_sheet = workbook.active
        applications_sheet.title = "Vagas"
        self._prepare(applications_sheet, self._APPLICATION_HEADERS)
        for application in applications:
            self._append_application(applications_sheet, application)

        questions_sheet = workbook.create_sheet("Perguntas")
        self._prepare(questions_sheet, self._QUESTION_HEADERS)
        for question in questions:
            self._append_question(questions_sheet, question)

        self._save(workbook)

    def _prepare(self, sheet: Worksheet, headers: Sequence[tuple[str, int]]) -> None:
        sheet.append([header for header, _ in headers])
        for cell, (_, width) in zip(sheet[1], headers, strict=True):
            cell.font = self._HEADER_FONT
            cell.fill = self._HEADER_FILL
            sheet.column_dimensions[cell.column_letter].width = width
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

    def _append_application(self, sheet: Worksheet, application: JobApplication) -> None:
        resume_file = self._project_root / application.resume_path
        sheet.append(
            [
                application.created_at,
                application.company,
                application.title,
                application.location,
                self._STATUS_LABELS[application.status],
                application.fit_percentage / 100,
                application.focus,
                application.locale,
                "Sim" if application.is_support_role else "Não",
                ", ".join(application.matched_terms),
                ", ".join(application.missing_terms),
                resume_file.name,
                "Abrir" if application.url else None,
                application.updated_at,
            ]
        )
        row = sheet[sheet.max_row]
        row[0].number_format = row[13].number_format = self._DATE_FORMAT
        row[5].number_format = "0%"
        self._link(row[11], Path(os.path.relpath(resume_file, self._path.parent)).as_posix())
        if application.url:
            self._link(row[12], application.url)
        sheet.auto_filter.ref = sheet.dimensions

    def _append_question(self, sheet: Worksheet, question: UnknownQuestion) -> None:
        last_job = f"{question.last_company} - {question.last_title}" if question.last_company else None
        sheet.append([question.question, question.occurrences, last_job, question.first_seen_at, question.last_seen_at])
        row = sheet[sheet.max_row]
        row[3].number_format = row[4].number_format = self._DATE_FORMAT
        sheet.auto_filter.ref = sheet.dimensions

    def _link(self, cell: Cell, target: str) -> None:
        cell.hyperlink = target
        cell.font = self._LINK_FONT

    def _save(self, workbook: Workbook) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_name(f"~{self._path.stem}.tmp.xlsx")
        workbook.save(temporary)
        try:
            os.replace(temporary, self._path)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise SpreadsheetLockedError(
                f"Não foi possível atualizar {self._path} (ela está aberta no Excel?). "
                "Os dados estão salvos no banco e a planilha será atualizada na próxima execução."
            ) from error
