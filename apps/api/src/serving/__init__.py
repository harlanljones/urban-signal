"""Model serving and real-time inference microservice modules."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.serving.app import create_app
    from src.serving.dispatcher import WebhookDispatcher
    from src.serving.engine import MultiHorizonInferenceEngine

__all__ = [
    "MultiHorizonInferenceEngine",
    "WebhookDispatcher",
    "create_app",
]


def __getattr__(name: str) -> Any:
    """Load serving entry points on demand to keep submodule imports acyclic."""
    if name == "create_app":
        from src.serving.app import create_app

        return create_app
    if name == "MultiHorizonInferenceEngine":
        from src.serving.engine import MultiHorizonInferenceEngine

        return MultiHorizonInferenceEngine
    if name == "WebhookDispatcher":
        from src.serving.dispatcher import WebhookDispatcher

        return WebhookDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
