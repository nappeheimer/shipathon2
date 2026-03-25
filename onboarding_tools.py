import asyncio
from typing import List
from pydantic import BaseModel, Field

# --- 1. SCHEMAS (Strict Constrained Decoding Rules) ---

class AccountProvisionerRequest(BaseModel):
    """Establishes digital identity and enforces Role-Based Access Control."""
    employee_id: str = Field(..., description="Unique identifier for the employee")
    role: str = Field(..., description="The designated job role for access scoping")
    requested_systems: List[str] = Field(..., description="Array of systems to grant access to")

class WelcomeEmailRequest(BaseModel):
    """Delivers automated, personalized introductory communications."""
    employee_name: str = Field(..., description="Full name of the new employee")
    manager_name: str = Field(..., description="Full name of the reporting manager")
    start_date: str = Field(..., description="ISO 8601 formatted start date")
    department: str = Field(..., description="The department the employee is joining")

class CalendarSchedulerRequest(BaseModel):
    """Automates time-blocking for orientation and training sessions."""
    employee_email: str = Field(..., description="Email address of the new employee")
    meeting_type: str = Field(..., description="Type of meeting (e.g., Orientation, IT Setup)")
    duration_minutes: int = Field(..., description="Duration of the meeting in minutes")
    participants: List[str] = Field(..., description="Array of participant email addresses")

class DocumentGeneratorRequest(BaseModel):
    """Automates creation of legally binding paperwork and NDAs."""
    employee_name: str = Field(..., description="Full name of the employee")
    job_title: str = Field(..., description="Official job title")
    salary_band: int = Field(..., description="Integer representation of the salary band")
    template_id: str = Field(..., description="Identifier for the specific document template")

class OnboardingTrackerRequest(BaseModel):
    """Updates the central system of record and closes the loop."""
    employee_id: str = Field(..., description="Unique identifier for the employee")
    status_code: int = Field(..., description="Integer code representing current onboarding status")
    completion_timestamp: str = Field(..., description="ISO 8601 datetime of completion")


# --- 2. THE TOOLSET CLASS (The Mock APIs) ---

class OnboardingToolset:
    """Mock API implementations for the onboarding workflow."""
    
    async def account_provisioner(self, request: AccountProvisionerRequest) -> str:
        # Simulating API latency
        await asyncio.sleep(0.5)
        return f"SUCCESS: Account provisioned for {request.employee_id} as {request.role} in {', '.join(request.requested_systems)}."

    async def welcome_email_composer(self, request: WelcomeEmailRequest) -> str:
        await asyncio.sleep(0.2)
        return f"SUCCESS: Welcome email drafted for {request.employee_name}. Manager: {request.manager_name}."

    async def calendar_scheduler(self, request: CalendarSchedulerRequest) -> str:
        await asyncio.sleep(0.3)
        return f"SUCCESS: {request.duration_minutes}-minute {request.meeting_type} scheduled for {request.employee_email}."

    async def document_generator(self, request: DocumentGeneratorRequest) -> str:
        await asyncio.sleep(0.8) # Documents naturally take longer to generate
        return f"SUCCESS: Document {request.template_id} generated for {request.employee_name} ({request.job_title})."

    async def onboarding_tracker(self, request: OnboardingTrackerRequest) -> str:
        await asyncio.sleep(0.1)
        return f"SUCCESS: Tracker updated for {request.employee_id} to status {request.status_code}."

    def get_tools(self) -> dict:
        """Returns the dictionary mapping tool names to their execution functions."""
        return {
            'account_provisioner': self.account_provisioner,
            'welcome_email_composer': self.welcome_email_composer,
            'calendar_scheduler': self.calendar_scheduler,
            'document_generator': self.document_generator,
            'onboarding_tracker': self.onboarding_tracker,
        }