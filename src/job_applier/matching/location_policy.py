from collections.abc import Sequence

from job_applier.matching.text_normalizer import TextNormalizer
from job_applier.matching.word_filter import WordFilter
from job_applier.models.automation_settings import WorkplaceType


class LocationPolicy:
    """Onde o candidato aceita trabalhar: presencial e híbrido só nas cidades aceitas, fora delas só remoto.

    O local da vaga vem como o LinkedIn mostra ("São Paulo, SP", "São Paulo e Região", "Brasil"): vale a
    primeira parte, a cidade, para que "Barueri, São Paulo, Brasil" (o estado) não passe por São Paulo.
    Sem modalidade na página, uma vaga fora das cidades aceitas só passa se o título disser que é remota.
    Sem cidades aceitas configuradas, nada é filtrado.
    """

    _REMOTE_IN_TITLE = WordFilter(["remoto", "remota", "remote", "home office", "100% remoto"])
    _MODALITY_NAMES = {WorkplaceType.ON_SITE: "Presencial", WorkplaceType.HYBRID: "Híbrida"}
    _METRO_AREA_SUFFIX = " e regiao"

    def __init__(self, on_site_cities: Sequence[str]) -> None:
        self._cities = tuple(TextNormalizer.normalize(city) for city in on_site_cities)
        self._city_names = ", ".join(on_site_cities)
        self._city_filter = WordFilter(list(on_site_cities)) if on_site_cities else None

    def skip_reason(self, workplace: WorkplaceType | None, title: str, location: str | None) -> str | None:
        if not self._cities or self._is_remote(workplace, title) or self.accepts_on_site_in(location):
            return None
        modality = self._MODALITY_NAMES.get(workplace, "Sem modalidade remota")
        return f"{modality} fora de {self._city_names} ({location or 'local não informado'})"

    def accepts_on_site_in(self, location: str | None) -> bool:
        city = self._city_of(location)
        return any(city in (accepted, f"{accepted}{self._METRO_AREA_SUFFIX}") for accepted in self._cities)

    def mentions_accepted_city(self, text: str) -> bool:
        return self._city_filter is not None and self._city_filter.first_match_in(text) is not None

    def names_another_city(self, location: str | None) -> bool:
        """O local é uma cidade ou região (tem vírgula ou "e Região"), não só o país, e não é uma das aceitas."""
        normalized = TextNormalizer.normalize(location or "")
        is_specific = "," in normalized or normalized.endswith(self._METRO_AREA_SUFFIX)
        return is_specific and not self.accepts_on_site_in(location)

    def _is_remote(self, workplace: WorkplaceType | None, title: str) -> bool:
        if workplace is not None:
            return workplace is WorkplaceType.REMOTE
        return self._REMOTE_IN_TITLE.first_match_in(title) is not None

    @staticmethod
    def _city_of(location: str | None) -> str:
        return TextNormalizer.normalize((location or "").split(",")[0]).strip()
