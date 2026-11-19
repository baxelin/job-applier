import pytest

from job_applier.answering.brazilian_location import BrazilianLocation


@pytest.mark.parametrize(
    "location",
    [
        "Brasil",
        "Brazil",
        "Belo Horizonte, Minas Gerais, Brazil",
        "Rio de Janeiro e Região",
        "Greater São Paulo Area",
        "Curitiba, Paraná",
    ],
)
def test_recognizes_places_in_brazil(location):
    assert BrazilianLocation().contains(location)


@pytest.mark.parametrize("location", ["Austin, Texas, United States", "Lisboa, Portugal", "Remote", "", None])
def test_anything_else_is_not_brazil(location):
    assert not BrazilianLocation().contains(location)
