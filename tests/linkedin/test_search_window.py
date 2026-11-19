from datetime import datetime

from job_applier.linkedin.search_window import SearchWindow
from job_applier.models.automation_settings import SearchQuery

NOW = datetime(2026, 11, 20, 9, 30)
SEARCH = SearchQuery(keywords="Desenvolvedor Júnior", location="São Paulo, SP")


class FakeProgress:
    def __init__(self, last: datetime | None = None) -> None:
        self.last = last
        self.marked: list[tuple[str, datetime]] = []

    def last_completed(self, search_key: str) -> datetime | None:
        return self.last

    def mark_completed(self, search_key: str, started_at: datetime) -> None:
        self.marked.append((search_key, started_at))


class TestSearchWindow:
    def test_a_search_never_completed_uses_the_maximum_window(self):
        assert SearchWindow(720, 24, FakeProgress(), lambda: NOW).hours_for(SEARCH) == 720

    def test_after_a_completed_search_asks_only_for_what_is_new_plus_a_margin(self):
        progress = FakeProgress(datetime(2026, 11, 19, 9, 0))

        assert SearchWindow(720, 24, progress, lambda: NOW).hours_for(SEARCH) == 25 + 24

    def test_never_goes_beyond_the_maximum_window(self):
        progress = FakeProgress(datetime(2026, 9, 1, 9, 0))

        assert SearchWindow(720, 24, progress, lambda: NOW).hours_for(SEARCH) == 720

    def test_without_progress_storage_keeps_the_maximum_window(self):
        assert SearchWindow(720, 24, None, lambda: NOW).hours_for(SEARCH) == 720

    def test_changing_the_search_makes_it_a_new_one(self):
        remote = SEARCH.model_copy(update={"workplace_types": ["remote"]})

        assert SEARCH.key() != remote.key()
