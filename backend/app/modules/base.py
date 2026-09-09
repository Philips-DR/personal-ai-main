from abc import ABC, abstractmethod

from app.models.orchestrator import Intent, ModuleRequest, ModuleResponse


class ModuleHandler(ABC):
    """Abstract base class for all assistant modules.

    Each module handles a specific set of intents and is completely
    independent — modules never import or call each other directly.
    Inter-module communication happens via follow_up_intents in ModuleResponse.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique module identifier, e.g. 'email', 'meeting'."""

    @property
    @abstractmethod
    def supported_intents(self) -> list[Intent]:
        """List of intents this module handles."""

    @abstractmethod
    async def handle(self, request: ModuleRequest) -> ModuleResponse:
        """Process a module request and return a response.

        Args:
            request: Contains intent, user message, extracted parameters,
                     memory context, and conversation history.

        Returns:
            ModuleResponse with content, optional structured data,
            pending actions requiring user approval, memory updates,
            and optional follow-up intents for the orchestrator to chain.
        """
