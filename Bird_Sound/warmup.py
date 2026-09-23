"""Load the ML models when a gunicorn worker starts instead of on the first request.

Lazy loading made the first classify/search after every restart wait ~20 s. Loading runs in a
background thread so the worker serves other endpoints meanwhile; a request that arrives
mid-load waits on the singleton's lock rather than loading a second copy."""
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)


def _load_models() -> None:
    from .classifier import get_classifier
    from .semantic_search import get_semantic_search

    for name, loader in (("classifier", get_classifier), ("semantic search", get_semantic_search)):
        try:
            loader()
        except Exception:
            logger.exception("Preloading %s failed; it will load on first use instead", name)


def start_model_warmup() -> None:
    if settings.PRELOAD_ML_MODELS:
        threading.Thread(target=_load_models, name="ml-warmup", daemon=True).start()
