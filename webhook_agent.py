import os
import logging
import json
import asyncio
import uuid
import audit_store
from datetime import datetime, timezone
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from onboarding_tools import (
    OnboardingToolset,
    AccountProvisionerRequest,
    WelcomeEmailRequest,
    CalendarSchedulerRequest,
    DocumentGeneratorRequest,
    OnboardingTrackerRequest
)

logger = logging.getLogger(__name__)


# ====================================================================== #
#  DAG SCHEMA                                                             #
# ====================================================================== #

class WorkflowStep(BaseModel):
    step_id: int = Field(..., description="The sequence number of this step.")
    tool_name: str = Field(..., description="MUST be exactly one of: account_provisioner, welcome_email_composer, calendar_scheduler, document_generator, onboarding_tracker")
    parameters: Dict[str, Any] = Field(..., description="The JSON arguments matching the specific tool's required schema.")

class WorkflowPlan(BaseModel):
    plan: List[WorkflowStep] = Field(..., description="The sequential Directed Acyclic Graph of tasks to execute.")


# ====================================================================== #
#  AUDIT LOG HELPERS                                                      #
#  These small functions build each section of the structured log.        #
# ====================================================================== #

def _now() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _make_workflow_metadata(
    workflow_id: str,
    session_id: str,
    original_instruction: str,
    timestamp_start: str,
) -> Dict:
    """
    Top-level metadata block.
    final_status and timestamp_end are filled in at the end of the run.
    """
    return {
        "workflow_id": workflow_id,
        "session_id": session_id,
        "original_instruction": original_instruction,
        "timestamp_start": timestamp_start,
        "timestamp_end": None,          # filled in when workflow ends
        "final_status": None,           # "complete" | "escalated" | "error"
        "total_steps_planned": 0,       # filled in after planning
        "total_steps_succeeded": 0,     # incremented on each success
        "total_retries": 0,             # incremented on each retry attempt
        "escalations": 0,               # incremented if escalation fires
    }


def _make_step_trace(
    step_id: int,
    tool_name: str,
    parameters_used: Dict,
) -> Dict:
    """
    One entry in execution_trace — one per step attempt.
    Fields are filled in progressively as the step runs.
    """
    return {
        "step_id": step_id,
        "tool_name": tool_name,
        "timestamp_start": _now(),
        "timestamp_end": None,
        "status": None,                 # "success" | "failed" | "escalated"
        "attempt_count": 0,
        "action": {
            "parameters_used": parameters_used,
        },
        "outcome": {
            "result": None,
            "error_details": None,
        },
        "recovery": {
            "retry_triggered": False,
            "attempts": [],             # list of {attempt, error, corrected_params}
            "escalated": False,
            "escalation_payload": None,
        },
    }


# ====================================================================== #
#  ORCHESTRATOR                                                            #
# ====================================================================== #

class OnboardingOrchestrator:
    def __init__(self):
        self.toolset = OnboardingToolset()
        self.available_tools = self.toolset.get_tools()

        self.schema_map = {
            'account_provisioner':    AccountProvisionerRequest,
            'welcome_email_composer': WelcomeEmailRequest,
            'calendar_scheduler':     CalendarSchedulerRequest,
            'document_generator':     DocumentGeneratorRequest,
            'onboarding_tracker':     OnboardingTrackerRequest,
        }

        self.api_key = os.getenv("ALT_API_KEY")
        if not self.api_key:
            logger.warning("ALT_API_KEY is missing!")

        self.llm_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    # ------------------------------------------------------------------ #
    # PLANNER                                                             #
    # ------------------------------------------------------------------ #
    async def generate_plan(self, user_instruction: str) -> WorkflowPlan:
        tool_docs = ""
        for name, schema in self.schema_map.items():
            schema_info = schema.model_json_schema()
            tool_docs += f"Tool: {name}\nRequired Parameters: {json.dumps(schema_info['properties'])}\n\n"

        system_prompt = f"""
        You are an elite enterprise workflow orchestrator.
        Decompose the user's onboarding request into a strict, sequential plan.

        AVAILABLE TOOLS AND THEIR STRICT SCHEMAS:
        {tool_docs}

        YOU MUST FOLLOW THIS EXACT STEP ORDER — NO EXCEPTIONS:
        1. account_provisioner      — provision system access first, everything else depends on this
        2. welcome_email_composer   — send welcome email once account exists
        3. calendar_scheduler       — schedule orientation meeting
        4. document_generator       — generate contract/NDA documents
        5. onboarding_tracker       — mark onboarding complete LAST, only after all steps done

        RULES:
        - You may ONLY use the 5 tools listed above in the order above.
        - You MUST use the exact parameter keys required by each tool's schema.
        - Do NOT execute the steps.
        - If required data is missing, infer reasonable corporate defaults.
        - onboarding_tracker must ALWAYS be the final step, never the first.

        You MUST output valid JSON exactly matching this schema:
        {{
        "plan": [
            {{
            "step_id": 1,
            "tool_name": "exact_tool_name",
            "parameters": {{"exact_key_from_schema": "value"}}
            }}
        ]
        }}
                """

        response = await self.llm_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_instruction}
            ],
            response_format={"type": "json_object"},
        )

        raw_json_string = response.choices[0].message.content
        return WorkflowPlan.model_validate_json(raw_json_string)

    # ------------------------------------------------------------------ #
    # CORRECTOR                                                           #
    # ------------------------------------------------------------------ #
    async def generate_corrected_params(
        self,
        tool_name: str,
        failed_params: Dict[str, Any],
        error_message: str,
    ) -> Dict[str, Any]:
        schema_class = self.schema_map[tool_name]
        schema_info  = schema_class.model_json_schema()

        prompt = f"""
You are a parameter correction engine.

A tool call failed with the following error:
ERROR: {error_message}

Tool name: {tool_name}
Tool schema (required parameters and types): {json.dumps(schema_info['properties'])}

The parameters that caused the failure:
{json.dumps(failed_params, indent=2)}

Analyse the error carefully. Return ONLY a corrected JSON object whose keys exactly match the tool schema.
Fix the problem that caused the error. Do NOT repeat the same values that failed.
Common fixes:
- Wrong type (e.g. string instead of integer) → correct the type
- Missing or null required field → infer a sensible corporate default
- Rejected value (e.g. unknown system name) → substitute a standard alternative

Output ONLY the corrected parameters JSON object, nothing else.
        """

        response = await self.llm_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    # ------------------------------------------------------------------ #
    # ESCALATION BUILDER                                                  #
    # ------------------------------------------------------------------ #
    def build_escalation_payload(
        self,
        original_instruction: str,
        completed_steps: List[Dict],
        failed_tool: str,
        failed_step_id: int,
        all_errors: List[str],
        all_attempted_params: List[Dict],
    ) -> Dict:
        return {
            "escalation": True,
            "escalation_timestamp": _now(),
            "original_goal": original_instruction,
            "summary": (
                f"Step {failed_step_id} (`{failed_tool}`) could not be completed "
                f"after the maximum number of retries. Human review required."
            ),
            "completed_steps": completed_steps,
            "failed_step": {
                "step_id": failed_step_id,
                "tool_name": failed_tool,
                "max_retries_reached": True,
                "error_history": all_errors,
                "parameter_attempts": all_attempted_params,
            },
            "recommended_action": (
                f"Please manually execute `{failed_tool}` with the last attempted "
                f"parameters, or investigate the underlying system error."
            ),
        }

    # ------------------------------------------------------------------ #
    # EXECUTOR  ←  main entry point                                       #
    # ------------------------------------------------------------------ #
    async def process_request(self, session_id: str, message: str) -> str:
        logger.info(f"Received request: {message}")

        # ── Bootstrap the audit log ──────────────────────────────────── #
        workflow_id    = f"wf-{uuid.uuid4().hex[:8]}"
        timestamp_start = _now()

        audit_log: Dict = {
            "workflow_metadata": _make_workflow_metadata(
                workflow_id=workflow_id,
                session_id=session_id,
                original_instruction=message,
                timestamp_start=timestamp_start,
            ),
            "planned_steps": [],        # filled in after generate_plan()
            "execution_trace": [],      # one entry per step
        }

        meta = audit_log["workflow_metadata"]   # shorthand reference

        try:
            # ── Plan ─────────────────────────────────────────────────── #
            logger.info("Generating Plan via Groq...")
            workflow_plan = await self.generate_plan(message)

            # Record the plan in the audit log
            audit_log["planned_steps"] = [
                {"step_id": s.step_id, "tool_name": s.tool_name, "parameters": s.parameters}
                for s in workflow_plan.plan
            ]
            meta["total_steps_planned"] = len(workflow_plan.plan)

            # Track completed steps for escalation payload
            completed_steps: List[Dict] = []

            # ── Execute step by step ──────────────────────────────────── #
            for step in workflow_plan.plan:
                tool_name     = step.tool_name
                current_params = dict(step.parameters)

                # Create trace record for this step
                trace = _make_step_trace(step.step_id, tool_name, current_params)
                audit_log["execution_trace"].append(trace)

                if tool_name not in self.available_tools:
                    trace["status"] = "failed"
                    trace["timestamp_end"] = _now()
                    trace["outcome"]["error_details"] = f"Tool '{tool_name}' not found in toolset."
                    continue

                MAX_RETRIES   = 2
                tool_function = self.available_tools[tool_name]
                schema_class  = self.schema_map[tool_name]
                step_succeeded = False

                all_errors:           List[str]  = []
                all_attempted_params: List[Dict] = []

                for attempt in range(MAX_RETRIES + 1):   # 0, 1, 2
                    trace["attempt_count"] = attempt + 1

                    # ── Pydantic validation ───────────────────────────── #
                    try:
                        all_attempted_params.append(dict(current_params))
                        validated_request = schema_class(**current_params)

                    except Exception as validation_err:
                        error_str = str(validation_err)
                        all_errors.append(f"Attempt {attempt + 1} [validation]: {error_str}")
                        meta["total_retries"] += 1

                        attempt_record = {
                            "attempt": attempt + 1,
                            "error_type": "validation",
                            "error": error_str,
                            "corrected_params": None,
                        }

                        if attempt < MAX_RETRIES:
                            trace["recovery"]["retry_triggered"] = True
                            corrected = await self.generate_corrected_params(
                                tool_name=tool_name,
                                failed_params=current_params,
                                error_message=error_str,
                            )
                            current_params = corrected
                            attempt_record["corrected_params"] = corrected
                            trace["recovery"]["attempts"].append(attempt_record)
                            # Update the action record with the latest params
                            trace["action"]["parameters_used"] = current_params
                            continue
                        else:
                            trace["recovery"]["attempts"].append(attempt_record)
                            break   # fall through to escalation

                    # ── Tool execution ────────────────────────────────── #
                    try:
                        result = await tool_function(validated_request)

                        # SUCCESS — fill in trace and move on
                        trace["status"]               = "success"
                        trace["timestamp_end"]        = _now()
                        trace["outcome"]["result"]    = result
                        step_succeeded                = True
                        meta["total_steps_succeeded"] += 1

                        completed_steps.append({
                            "step_id":   step.step_id,
                            "tool_name": tool_name,
                            "status":    "success",
                            "result":    result,
                        })
                        break

                    except Exception as tool_err:
                        error_str = str(tool_err)
                        all_errors.append(f"Attempt {attempt + 1} [execution]: {error_str}")
                        meta["total_retries"] += 1
                        wait_time = 2 ** attempt

                        attempt_record = {
                            "attempt":    attempt + 1,
                            "error_type": "execution",
                            "error":      error_str,
                            "corrected_params": None,
                        }

                        if attempt < MAX_RETRIES:
                            trace["recovery"]["retry_triggered"] = True
                            is_transient = any(
                                kw in error_str.lower()
                                for kw in ["timeout", "rate limit", "429", "503", "connection"]
                            )

                            if is_transient:
                                attempt_record["strategy"] = f"backoff_{wait_time}s"
                                await asyncio.sleep(wait_time)
                                # params unchanged for transient errors
                            else:
                                corrected = await self.generate_corrected_params(
                                    tool_name=tool_name,
                                    failed_params=current_params,
                                    error_message=error_str,
                                )
                                current_params = corrected
                                attempt_record["corrected_params"] = corrected
                                attempt_record["strategy"] = "modified_params"
                                trace["action"]["parameters_used"] = current_params

                            trace["recovery"]["attempts"].append(attempt_record)
                        else:
                            trace["recovery"]["attempts"].append(attempt_record)
                            # last attempt — loop ends

                # ── Escalation check ──────────────────────────────────── #
                if not step_succeeded:
                    escalation_payload = self.build_escalation_payload(
                        original_instruction=message,
                        completed_steps=completed_steps,
                        failed_tool=tool_name,
                        failed_step_id=step.step_id,
                        all_errors=all_errors,
                        all_attempted_params=all_attempted_params,
                    )

                    # Write escalation into the trace record
                    trace["status"]                          = "escalated"
                    trace["timestamp_end"]                   = _now()
                    trace["outcome"]["error_details"]        = all_errors
                    trace["recovery"]["escalated"]           = True
                    trace["recovery"]["escalation_payload"]  = escalation_payload

                    meta["escalations"] += 1
                    meta["final_status"]    = "escalated"
                    meta["timestamp_end"]   = _now()

                    logger.error(
                        f"Escalation triggered for step {step.step_id} ({tool_name}). "
                        f"Errors: {all_errors}"
                    )
                    break   # halt — don't run remaining steps

            # ── Finalise the audit log ────────────────────────────────── #
            if meta["final_status"] is None:
                meta["final_status"]  = "complete"
            if meta["timestamp_end"] is None:
                meta["timestamp_end"] = _now()
            audit_store.save_log(audit_log)
            return json.dumps(audit_log, indent=2)

        except Exception as e:
            meta["final_status"]  = "error"
            meta["timestamp_end"] = _now()
            audit_log["fatal_error"] = str(e)
            logger.exception("Fatal error during orchestration")
            audit_store.save_log(audit_log)
            return json.dumps(audit_log, indent=2)


def create_agent():
    orchestrator = OnboardingOrchestrator()
    return {
        "name":        "onboarding_agent",
        "description": "Executes strict Plan-then-Execute employee onboarding.",
        "version":     "1.0.0",
        "agent_instance": orchestrator,
    }