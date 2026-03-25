import logging
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCard, TextPart, UnsupportedOperationError
from a2a.utils.errors import ServerError

# Import our new brain
from webhook_agent import OnboardingOrchestrator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class OnboardingAgentExecutor(AgentExecutor):
    """An AgentExecutor that routes A2A requests to our P-t-E Orchestrator."""

    def __init__(
        self,
        card: AgentCard,
        orchestrator: OnboardingOrchestrator,
    ):
        self._card = card
        self.orchestrator = orchestrator
        logger.info("OnboardingAgentExecutor initialized")

    async def _process_request(
        self,
        message_text: str,
        request_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        """Passes the message to the AI Brain and returns the response."""
        try:
            logger.info(f"Processing message: {message_text}")
            
            # Send message to our AI Brain
            brain_response = await self.orchestrator.process_request(
                session_id=request_id, message=message_text
            )

            # Create response artifact and complete the task
            response_part = TextPart(text=brain_response)
            await task_updater.add_artifact([response_part])
            await task_updater.complete()

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            error_message = f"Failed to process request: {str(e)}"
            await task_updater.add_artifact([TextPart(text=error_message)])
            await task_updater.complete()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        message_text = ""
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                message_text += part.root.text

        session_id = context.context_id
        await self._process_request(message_text, session_id, updater)

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())