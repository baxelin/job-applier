import signal

import pytest

from job_applier.termination import TerminationRequested, TerminationSignal


class TestTerminationSignal:
    def test_sigterm_becomes_an_exception_that_passes_through_except_exception(self):
        caught_as_exception = False

        with pytest.raises(TerminationRequested), TerminationSignal():
            try:
                signal.raise_signal(signal.SIGTERM)
            except Exception:
                caught_as_exception = True

        assert not caught_as_exception

    def test_restores_the_previous_handler(self):
        previous = signal.getsignal(signal.SIGTERM)

        with TerminationSignal():
            assert signal.getsignal(signal.SIGTERM) is not previous

        assert signal.getsignal(signal.SIGTERM) is previous
