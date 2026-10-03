"""
Top-level pytest setup for the whole `backend/` tree.

Lives here (not in `backend/tests/conftest.py`) specifically so it applies to
every test directory under `backend/` -- including `backend/src/*/tests/` --
since conftest.py fixtures only auto-apply to their own directory and its
subdirectories, and `backend/tests/` and `backend/src/*/tests/` are siblings,
not nested.
"""

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    Reset the shared rate limiter's in-memory counters before each test.

    Without this, the limiter (module-level, process-wide) carries state
    across every test function in the session. Since TestClient requests all
    share the same source address, a handful of tests each calling
    /auth/login or /auth/signup once would exhaust the real 5/minute limit
    partway through the suite and start failing unrelated tests with 429s
    that have nothing to do with what those tests are actually checking.
    """
    from rate_limit import limiter

    limiter.reset()
    yield
