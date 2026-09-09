import logging

from app.models.orchestrator import Intent
from app.modules.base import ModuleHandler

logger = logging.getLogger(__name__)


class ModuleRouter:
    """Registry that maps intents to module handlers.

    Modules register themselves at startup. The orchestrator calls route()
    to find the correct handler for a classified intent.
    """

    def __init__(self) -> None:
        self._handlers: dict[Intent, ModuleHandler] = {}
        self._modules: list[ModuleHandler] = []

    def register(self, handler: ModuleHandler) -> None:
        """Register a module handler for its supported intents."""
        self._modules.append(handler)
        for intent in handler.supported_intents:
            if intent in self._handlers:
                logger.warning(
                    "Intent '%s' already registered to '%s', overwriting with '%s'",
                    intent,
                    self._handlers[intent].name,
                    handler.name,
                )
            self._handlers[intent] = handler
        logger.info("Registered module '%s' for intents: %s", handler.name, handler.supported_intents)

    def route(self, intent: Intent) -> ModuleHandler:
        """Find the handler for a given intent.

        Raises KeyError if no handler is registered for the intent.
        """
        if intent not in self._handlers:
            raise KeyError(f"No module registered for intent '{intent}'")
        return self._handlers[intent]

    @property
    def registered_intents(self) -> list[Intent]:
        return list(self._handlers.keys())

    @property
    def registered_modules(self) -> list[ModuleHandler]:
        return list(self._modules)
