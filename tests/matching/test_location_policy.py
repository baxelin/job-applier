import pytest

from job_applier.matching.location_policy import LocationPolicy
from job_applier.models.automation_settings import WorkplaceType

POLICY = LocationPolicy(["São Paulo"])


class TestLocationPolicy:
    @pytest.mark.parametrize("location", ["São Paulo, SP", "São Paulo, São Paulo, Brasil", "São Paulo e Região"])
    def test_on_site_and_hybrid_are_accepted_in_the_city(self, location):
        assert POLICY.skip_reason(WorkplaceType.ON_SITE, "Dev Júnior", location) is None
        assert POLICY.skip_reason(WorkplaceType.HYBRID, "Dev Júnior", location) is None

    @pytest.mark.parametrize("location", ["Rio de Janeiro, RJ", "Barueri, São Paulo, Brasil", "Brasil", None])
    def test_outside_the_city_only_remote_is_accepted(self, location):
        assert POLICY.skip_reason(WorkplaceType.REMOTE, "Dev Júnior", location) is None
        assert POLICY.skip_reason(WorkplaceType.ON_SITE, "Dev Júnior", location).startswith("Presencial fora de")
        assert POLICY.skip_reason(WorkplaceType.HYBRID, "Dev Júnior", location).startswith("Híbrida fora de")

    def test_without_workplace_the_title_decides(self):
        assert POLICY.skip_reason(None, "Dev Júnior | Remoto", "Brasil") is None
        assert POLICY.skip_reason(None, "Dev Júnior", "Curitiba, PR") == (
            "Sem modalidade remota fora de São Paulo (Curitiba, PR)"
        )

    def test_without_accepted_cities_nothing_is_filtered(self):
        assert LocationPolicy([]).skip_reason(WorkplaceType.ON_SITE, "Dev", "Recife, PE") is None

    def test_tells_a_city_from_a_country(self):
        assert POLICY.names_another_city("Rio de Janeiro e Região")
        assert POLICY.names_another_city("Curitiba, PR")
        assert not POLICY.names_another_city("Brasil")
        assert not POLICY.names_another_city("São Paulo, SP")

    def test_finds_an_accepted_city_in_a_question(self):
        assert POLICY.mentions_accepted_city("Atuar 100% presencial na Vila Olimpia em São Paulo/SP?")
        assert not POLICY.mentions_accepted_city("Atuar presencial em Campinas?")
