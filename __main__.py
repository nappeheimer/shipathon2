import logging
import os
import click
import uvicorn
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.applications import Starlette
from starlette.routing import Route

from webhook_agent import create_agent
from webhook_agent_executor import OnboardingAgentExecutor
from ui_routes import get_ui_routes

load_dotenv()
logging.basicConfig(level=logging.INFO)

@click.command()
@click.option("--host", "host", default="0.0.0.0")
@click.option("--port", "port", default=5000)
def main(host: str, port: int):

    skill = AgentSkill(
        id="onboarding_orchestration",
        name="Employee Onboarding Orchestrator",
        description="Decomposes unstructured onboarding requests into a strict sequence of tool executions.",
        tags=["hr", "onboarding", "orchestration"],
        examples=[
            "Onboard Sarah Connor to the Cybersecurity team starting next Monday."
        ],
    )

    agent_card = AgentCard(
        name="Onboarding Agent",
        description="Executes strict Plan-then-Execute employee onboarding.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )

    agent_data = create_agent()

    agent_executor = OnboardingAgentExecutor(
        card=agent_card,
        orchestrator=agent_data["agent_instance"],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    # Combine A2A routes with our UI routes
    all_routes = a2a_app.routes() + get_ui_routes()
    app = Starlette(routes=all_routes)

    logging.info(f"Agent running at http://{host}:{port}")
    logging.info(f"Audit dashboard: http://{host}:{port}/ui")
    logging.info(f"Audit log JSON:  http://{host}:{port}/audit-log")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()