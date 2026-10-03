"""
Shared rate limiter (Wave C, Member 4 — Security Hardening).

A single `Limiter` instance, imported by both `main.py` (to register the
middleware and exception handler) and the route modules that need a tighter
limit than the rest of the API (`auth/routes.py`, `routes.py`). Living in its
own module -- rather than being constructed inside `main.py` -- is what keeps
this import-cycle-free: `main.py` already imports the route modules, so if
the route modules imported `limiter` back from `main`, that would be a
circular import.

Keyed by remote IP (`get_remote_address`) rather than by account, since the
endpoints this protects (login, signup) are exactly the ones where the
attacker doesn't have an account yet.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
