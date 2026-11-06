"""Pydantic schemas for DeployEasy REST API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    repo_name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$")
    branch: str = Field("main", max_length=50)
    service_url: str = Field("", max_length=255)
    deploy_hook_url: str = Field("", max_length=255)


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    status: str
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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentTriggerRequest(BaseModel):
    project_id: int
    commit_sha: str = Field(..., min_length=7, max_length=40)
    commit_message: str = Field("Manual deploy triggered via dashboard", max_length=255)
    branch: str = "main"


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
