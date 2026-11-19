from job_applier.models.answer_book import SkillYearsRule
from job_applier.models.glossary import Glossary
from job_applier.models.resume import Resume


class SkillExperience:
    """Experiência do candidato com cada tecnologia do glossário, a partir do CV.

    Tecnologia do CV vale os anos de lá. Fora do CV, mas derivada de uma que está nele (Django de Python,
    Next.js de React), vale related_years, quando a regra define esse valor. O resto vale default_years e
    não conta como conhecida.
    """

    def __init__(self, resume: Resume, glossary: Glossary, rule: SkillYearsRule) -> None:
        self._years_by_skill = {skill.term: skill.years for skill in resume.skills}
        self._related = {term.id: tuple(term.related_to) for term in glossary.terms}
        self._rule = rule

    def knows(self, term_id: str) -> bool:
        return term_id in self._years_by_skill or self._derives_from_the_resume(term_id)

    def years(self, term_id: str) -> float:
        if term_id in self._years_by_skill:
            return self._years_by_skill[term_id]
        if self._derives_from_the_resume(term_id):
            return self._rule.related_years
        return self._rule.default_years

    def _derives_from_the_resume(self, term_id: str) -> bool:
        if self._rule.related_years is None:
            return False
        return any(base in self._years_by_skill for base in self._related.get(term_id, ()))
