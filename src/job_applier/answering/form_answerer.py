from collections.abc import Sequence

from job_applier.answering.brazilian_location import BrazilianLocation
from job_applier.answering.option_matcher import OptionMatcher
from job_applier.answering.salary_calculator import SalaryCalculator
from job_applier.answering.skill_experience import SkillExperience
from job_applier.matching.keyword_extractor import KeywordExtractor
from job_applier.matching.word_filter import WordFilter
from job_applier.models.answer_book import Answer, AnswerBook, YearsArea
from job_applier.models.base import Locale
from job_applier.models.form_field import FieldAnswer, FieldKind, FormField
from job_applier.models.glossary import Glossary
from job_applier.models.job_application import JobApplication
from job_applier.models.resume import Resume


class FormAnswerer:
    """Responde um campo de formulário com as regras de respostas.json e os dados do CV.

    A ordem é: pretensão salarial, anos de experiência e respostas prontas (vence o padrão mais
    longo que aparecer na pergunta, o mais específico). Devolve None quando não há resposta segura; nesse
    caso a candidatura fica pendente. Nada é inventado: resposta null, pergunta de salário em vaga no
    exterior (a moeda ainda não foi definida) e campo de busca com sugestões ficam sempre sem resposta.
    Vaga em inglês localizada no Brasil recebe a pretensão em reais, como as vagas em português.
    """

    _CHOICE_KINDS = frozenset({FieldKind.SELECT, FieldKind.RADIO, FieldKind.CHECKBOX})
    _YES_OR_NO_KINDS = frozenset({FieldKind.SELECT, FieldKind.RADIO})
    _YES = {Locale.PT: "Sim", Locale.EN: "Yes"}
    _NO = {Locale.PT: "Não", Locale.EN: "No"}

    def __init__(
        self,
        answer_book: AnswerBook,
        resume: Resume,
        glossary: Glossary,
        matcher: OptionMatcher | None = None,
    ) -> None:
        self._skills = SkillExperience(resume, glossary, answer_book.skill_years)
        self._extractor = KeywordExtractor(glossary)
        self._salary = SalaryCalculator(answer_book.salary)
        self._salary_filter = WordFilter(answer_book.salary.patterns)
        self._years_filter = WordFilter(answer_book.skill_years.patterns)
        self._area_filters = [(area, WordFilter(area.patterns)) for area in answer_book.skill_years.areas]
        experience = answer_book.experience
        self._experience_filter = WordFilter(experience.patterns) if experience else None
        self._answer_filters = [(answer, WordFilter(answer.patterns)) for answer in answer_book.answers]
        self._matcher = matcher or OptionMatcher()
        self._brazil = BrazilianLocation()

    def answer(self, field: FormField, application: JobApplication) -> FieldAnswer | None:
        if field.kind is FieldKind.TYPEAHEAD:
            return None
        candidates = self._candidates(field, application)
        if not candidates:
            return None
        if field.kind in self._CHOICE_KINDS:
            return self._choice(field, candidates)
        return self._text(field, candidates[0])

    def _candidates(self, field: FormField, application: JobApplication) -> list[str]:
        """Respostas possíveis, primeiro no idioma da vaga; opções podem vir no outro idioma.

        Uma resposta pronta (inclusive null) vence a regra geral de experiência.
        """
        question = field.question
        locale = Locale(application.locale)
        if self._salary_filter.first_match_in(question):
            return self._salary_answer(question, application, locale)
        if self._years_filter.first_match_in(question):
            return self._years_answer(question)
        answer = self._best_answer(question)
        if answer is not None:
            if answer.answer is None:
                return []
            return [answer.answer.in_locale(locale), answer.answer.in_locale(self._other(locale))]
        return self._experience_answer(field, locale)

    @staticmethod
    def _other(locale: Locale) -> Locale:
        return Locale.EN if locale is Locale.PT else Locale.PT

    def _experience_answer(self, field: FormField, locale: Locale) -> list[str]:
        """Sim se todas as tecnologias citadas são conhecidas (CV ou derivadas dele), não se nenhuma é.

        Sem tecnologia do glossário, vale a área declarada em skill_years.areas ("desenvolvimento de software"):
        sim quando ela tem anos de experiência.
        """
        if field.kind not in self._YES_OR_NO_KINDS or self._experience_filter is None:
            return []
        if not self._experience_filter.first_match_in(field.question):
            return []
        terms = self._extractor.extract(field.question)
        if not terms:
            area = self._area_in(field.question)
            return [self._YES[locale], self._YES[self._other(locale)]] if area and area.years > 0 else []
        known = [self._skills.knows(term) for term in terms]
        if all(known):
            words = self._YES
        elif not any(known):
            words = self._NO
        else:
            return []
        return [words[locale], words[self._other(locale)]]

    def _salary_answer(self, question: str, application: JobApplication, locale: Locale) -> list[str]:
        if locale is not Locale.PT and not self._brazil.contains(application.location):
            return []
        return [str(self._salary.expectation(question, application.description or ""))]

    def _years_answer(self, question: str) -> list[str]:
        """Tecnologias do glossário vêm do CV; sem nenhuma, vale a área declarada que aparecer na pergunta."""
        terms = self._extractor.extract(question)
        if terms:
            return [f"{min(self._skills.years(term) for term in terms):g}"]
        area = self._area_in(question)
        return [f"{area.years:g}"] if area else []

    def _area_in(self, question: str) -> YearsArea | None:
        """A área declarada cujo padrão aparece na pergunta; vence o padrão mais longo."""
        matches = [
            (len(pattern), area)
            for area, patterns in self._area_filters
            if (pattern := patterns.first_match_in(question))
        ]
        return max(matches, key=lambda match: match[0], default=(0, None))[1]

    def _best_answer(self, question: str) -> Answer | None:
        matches = [
            (len(pattern), answer)
            for answer, patterns in self._answer_filters
            if (pattern := patterns.first_match_in(question))
        ]
        return max(matches, key=lambda match: match[0], default=(0, None))[1]

    def _choice(self, field: FormField, candidates: Sequence[str]) -> FieldAnswer | None:
        if field.kind is FieldKind.CHECKBOX:
            options = self._matcher.pick_many(field.options, candidates)
        else:
            option = self._matcher.pick(field.options, candidates)
            options = (option,) if option else ()
        return FieldAnswer.choosing(*options) if options else None

    @staticmethod
    def _text(field: FormField, text: str) -> FieldAnswer | None:
        if field.max_length is not None and len(text) > field.max_length:
            return None
        if field.kind is FieldKind.NUMBER and not text.replace(".", "", 1).isdigit():
            return None
        return FieldAnswer(text=text)
