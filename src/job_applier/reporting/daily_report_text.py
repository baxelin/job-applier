from job_applier.models.job_application import UnknownQuestion
from job_applier.reporting.daily_summary import DailySummary


class DailyReportText:
    """Texto curto do resumo do dia, para o terminal. Pendências zeradas não aparecem."""

    def render(self, summary: DailySummary) -> str:
        lines = [f"Resumo de {summary.day:%d/%m/%Y}", f"Enviadas: {len(summary.sent)}"]
        lines += [f"  - {item.company}: {item.title}" for item in summary.sent]
        lines.append(f"Vagas novas: {summary.seen} ({summary.with_resume} com CV, {summary.skipped} ignoradas)")
        lines += ["", *self._waiting(summary)]
        if summary.open_questions:
            lines += ["", "Perguntas que travam vagas (responder em personal/respostas.json):"]
            lines += [self._question(question, summary) for question in summary.open_questions]
        return "\n".join(lines)

    @staticmethod
    def _waiting(summary: DailySummary) -> list[str]:
        items = [
            (summary.ready_to_send, 'prontas para enviar: rode "aplicar"'),
            (summary.manual_pending, 'para aplicar no site da empresa (planilha, coluna "Link para aplicar")'),
            (summary.question_pending, 'pendentes de pergunta: depois de responder, rode "aplicar --repetir-pendentes"'),
            (len(summary.failed), "com erro: conferir no LinkedIn antes de tentar de novo"),
        ]
        waiting = [f"  - {count} {text}" for count, text in items if count]
        waiting += [f"      {item.company}: {item.title}" for item in summary.failed]
        return ["Esperando por você:", *waiting] if waiting else ["Nada esperando por você."]

    @staticmethod
    def _question(question: UnknownQuestion, summary: DailySummary) -> str:
        new = " [nova]" if question.first_seen_at.date() == summary.day else ""
        return f'  - "{question.question}" ({question.occurrences}x, última: {question.last_company}){new}'
