"""Pydantic schemas for DeployEasy REST API."""
from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    status: str = "authenticated"
    token: str
    csrf_token: str = ""
    user: UserResponse


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    repo_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$")
    branch: str = Field("main", max_length=50)
    service_url: str = Field("", max_length=255)


class ProjectCreate(ProjectBase):
    deploy_hook_url: str = Field("", max_length=255)
    repo_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_github_url(cls, values):
        if isinstance(values, dict) and not values.get("repo_name") and values.get("repo_url"):
            raw_repo = values["repo_url"].strip()
            parsed = urlparse(raw_repo if "://" in raw_repo else f"https://{raw_repo}")
            if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
                raise ValueError("Enter a GitHub repository URL such as https://github.com/owner/repo")
            parts = [part for part in parsed.path.strip("/").split("/") if part]
            if len(parts) != 2:
                raise ValueError("GitHub URL must point to a repository in owner/repo format")
            owner, repo = parts
            if repo.endswith(".git"):
                repo = repo[:-4]
            values = {**values, "repo_name": f"{owner}/{repo}"}
        return values


class GitHubRepositoryRequest(BaseModel):
    repo_url: str = Field(..., min_length=5, max_length=255)


class ProjectUpdate(BaseModel):
    name: str | None = None
    branch: str | None = None
    service_url: str | None = None
    deploy_hook_url: str | None = None


class RenderProvisionRequest(BaseModel):
    service_type: Literal["web_service", "static_site"] = "web_service"
    runtime: Literal["docker", "node", "python", "go", "ruby", "rust", "elixir"] = "node"
    region: Literal["oregon", "ohio", "virginia", "frankfurt", "singapore"] = "singapore"
    plan: Literal["free"] = "free"
    build_command: str = Field("npm install", max_length=500)
    start_command: str = Field("npm start", max_length=500)
    publish_path: str = Field("dist", max_length=200)


class ProjectResponse(ProjectBase):
    id: int
    status: str
    owner_id: int | None = None
    has_deploy_hook: bool = False
    render_service_created: bool = False
    render_deploy_status: Optional[str] = None
    last_probe_latency: Optional[float] = None
    last_probe_status: Optional[int] = None
    last_probe_healthy: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentResponse(BaseModel):
    id: int
    project_id: int
    commit_sha: str
    commit_message: str
    branch: str
    trigger_type: str
    status: str
    duration_seconds: int
    logs_summary: str
    workflow_run_id: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    model_config = ConfigDict(from_attributes=True)


class DeploymentTriggerRequest(BaseModel):
    project_id: int
    commit_sha: str = Field(..., min_length=7, max_length=40)
    commit_message: str = Field("Manual deploy triggered via dashboard", max_length=255)
    branch: str = "main"
    force: bool = False


class RollbackRequest(BaseModel):
    project_id: int
    target_sha: str = Field(..., min_length=7, max_length=40)
    reason: str = Field("Rollback triggered via dashboard", max_length=255)


class HealthCheckResponse(BaseModel):
    id: int
    project_id: int
    endpoint: str
    status_code: int
    response_time_ms: float
    is_healthy: bool
    error_message: str | None = None
    checked_at: datetime

    @field_serializer("checked_at")
    def serialize_checked_at(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    model_config = ConfigDict(from_attributes=True)


class SecurityScanResponse(BaseModel):
    id: int
    project_id: int
    scan_type: str
    target: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    passed: bool
    findings_json: str
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OverviewStats(BaseModel):
    total_projects: int
    active_deployments: int
    successful_deployments: int
    failed_deployments: int
    fleet_health: str
    avg_deploy_time_seconds: float
    process_uptime_seconds: float
    requests_served: int
    version: str
    git_sha: str
    recent_deployments: list[DeploymentResponse]
    projects: list[ProjectResponse]


class LogAnalysisRequest(BaseModel):
    logs: str = Field(..., min_length=1)


class LogAnalysisResponse(BaseModel):
    error_category: str
    severity: str
    summary: str
    root_cause: str
    suggested_fix: str
    detected: bool


class EnvValidationRequest(BaseModel):
    env_vars: dict[str, str]


class EnvValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    sanitized_variables: dict[str, str]
    variables_evaluated: int


class ChecklistItem(BaseModel):
    category: str
    status: str
    points: int
    message: str


class ReadinessResponse(BaseModel):
    readiness_score: int
    max_score: int
    confidence_tier: str
    badge_class: str
    recommendation: str
    checklist: list[ChecklistItem]
    deployment_blocked: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    evaluated_target: str = ""
    evaluated_at: str = ""



class CostBreakdown(BaseModel):
    github_actions_cost_usd: float
    hosting_cost_usd: float
    container_storage_cost_usd: float


class CostMetrics(BaseModel):
    total_deploy_minutes: float
    projected_monthly_minutes: float
    free_minutes_remaining: float
    container_image_size_mb: float
    images_stored_count: int
    instance_tier: str


class CostRecommendation(BaseModel):
    title: str
    impact: str
    suggestion: str


class CostEstimateResponse(BaseModel):
    projected_monthly_cost_usd: float
    breakdown: CostBreakdown
    metrics: CostMetrics
    recommendations: list[CostRecommendation]


class IncidentReportRequest(BaseModel):
    failed_sha: str = Field(..., min_length=7, max_length=64)
    rollback_sha: str | None = None
    symptoms: str = "Availability failure on /health"
    log_excerpt: str = ""


class IncidentReportResponse(BaseModel):
    title: str
    severity: str
    error_category: str
    failure_time: str
    recovery_time: str
    failed_sha: str
    rollback_sha: str | None
    symptoms: str
    root_cause: str
    suggested_fix: str
    markdown_report: str


class WebhookTestRequest(BaseModel):
    webhook_url: str = Field(..., min_length=10)
    platform: str = "discord"  # discord, slack, generic


class SystemModeInfo(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    description: str


class SystemModeResponse(BaseModel):
    current_mode: str
    available_modes: list[SystemModeInfo]


class SystemModeUpdateRequest(BaseModel):
    mode: str = Field(..., pattern=r"^(demo|sandbox|test)$")

