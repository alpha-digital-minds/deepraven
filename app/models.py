from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Profile sub-models ────────────────────────────────────────────────────────

class PersonalInfo(BaseModel):
    name: str = ""
    gender: str = ""
    phone: str = ""
    company: str = ""
    role: str = ""
    location: str = ""
    delivery_address: str = ""


class RelativeProfile(BaseModel):
    relation: str = ""          # e.g. daughter, son, wife, mother, friend
    name: str = ""              # if known
    age: str = ""               # e.g. "12", "~40"
    gender: str = ""
    preferences: list[str] = []
    sizes: dict[str, str] = {}  # e.g. {"shoes": "38", "clothes": "M"}
    notes: str = ""             # anything else worth knowing


class Preferences(BaseModel):
    communication_style: str = ""
    best_contact_channel: str = ""
    languages: list[str] = []


class SalesInfo(BaseModel):
    buying_persona: str = ""
    pain_points: list[str] = []
    objections_raised: list[str] = []
    buying_triggers: list[str] = []
    current_needs: list[str] = []
    budget_range: str = ""
    purchase_history: list[str] = []


class Relationship(BaseModel):
    status: str = ""
    last_contact_date: str = ""
    personal_details: list[str] = []


class UserProfile(BaseModel):
    # user_id is the contact's DB UUID — kept for LLM pipeline compatibility
    user_id: str
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    preferences: Preferences = Field(default_factory=Preferences)
    sales: SalesInfo = Field(default_factory=SalesInfo)
    relationship: Relationship = Field(default_factory=Relationship)
    relatives: list[RelativeProfile] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


# ── Conversation models ───────────────────────────────────────────────────────

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ConversationInput(BaseModel):
    messages: list[Message]
    metadata: Optional[dict[str, Any]] = None


class ConversationRecord(BaseModel):
    messages: list[Message]
    metadata: Optional[dict[str, Any]] = None
    timestamp: str = Field(default_factory=_utcnow)
    processed: bool = False


# ── Multi-tenant models ───────────────────────────────────────────────────────

class Project(BaseModel):
    id: str
    account_id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Contact(BaseModel):
    id: str
    project_id: str
    external_id: str
    created_at: str


class ContactSummary(BaseModel):
    id: str
    project_id: str
    external_id: str
    name: str
    company: str
    total_conversations: int
    unprocessed_count: int


class ApiKey(BaseModel):
    id: str
    project_id: str
    name: str
    created_at: str
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreateResponse(BaseModel):
    id: str
    project_id: str
    name: str
    created_at: str
    key: str  # raw key — shown ONCE, not stored


class AccountApiKey(BaseModel):
    id: str
    account_id: str
    name: str
    created_at: str
    last_used_at: Optional[str] = None
    revoked_at: Optional[str] = None


class AccountApiKeyCreate(BaseModel):
    name: str


class AccountApiKeyCreateResponse(BaseModel):
    id: str
    account_id: str
    name: str
    created_at: str
    key: str  # raw key — shown ONCE, not stored (prefix: dra_)


# ── API response models ───────────────────────────────────────────────────────

class AddConversationResponse(BaseModel):
    contact_id: str
    project_id: str
    conversations_added: int
    profile_update: str  # "scheduled" | "skipped"


class ProfileUpdateStatus(BaseModel):
    contact_id: str
    status: str  # "idle" | "processing"


# ── Auth models ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    email: str


class UpdatePasswordRequest(BaseModel):
    access_token: str   # from the recovery callback
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class OtpVerifyRequest(BaseModel):
    email: str
    token: str


class ResendOtpRequest(BaseModel):
    email: str


# ── Account config models ─────────────────────────────────────────────────────

class AccountConfigCreate(BaseModel):
    profile_schema: dict
    purpose_industry: str
    purpose_agent_type: str
    purpose_description: str


class AccountConfig(BaseModel):
    id: str
    account_id: str
    profile_schema: dict
    purpose_industry: str
    purpose_agent_type: str
    purpose_description: str
    prompt_extractor: str
    prompt_reviewer: str
    prompt_compressor: str
    created_at: str
    updated_at: str


class PromptsUpdate(BaseModel):
    prompt_extractor: Optional[str] = None
    prompt_reviewer: Optional[str] = None
    prompt_compressor: Optional[str] = None


class RegenerateRequest(BaseModel):
    comment: Optional[str] = None
