"""Shared Flask extensions — instantiated here, initialised in the app factory."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)
