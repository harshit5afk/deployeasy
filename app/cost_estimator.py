"""Cloud Infrastructure & CI/CD Pipeline Cost Estimator for DeployEasy.

Calculates GitHub Actions runner minutes, container registry storage,
cloud hosting costs, and provides actionable optimization recommendations.
"""
from typing import Any

# Pricing standards for small teams (as of 2026)
GITHUB_ACTIONS_LINUX_COST_PER_MIN = 0.008  # $0.008 per minute on standard GitHub-hosted runners
GITHUB_FREE_MINUTES_LIMIT = 2000           # 2,000 free minutes per month for public/private repos
RENDER_INSTANCE_PRICING = {
    "free": 0.0,
    "starter": 7.0,
    "standard": 25.0,
    "pro": 85.0,
}
GHCR_COST_PER_GB = 0.25                    # $0.25/GB/month after 500MB free allowance


def estimate_project_costs(
    deployment_durations_seconds: list[int],
    instance_tier: str = "free",
    container_image_size_mb: float = 185.0,
    images_stored_count: int = 5,
) -> dict[str, Any]:
    """Calculate monthly estimated infrastructure spend and cost-saving recommendations."""
    total_deploy_seconds = sum(deployment_durations_seconds) if deployment_durations_seconds else 0
    total_deploy_minutes = round(total_deploy_seconds / 60.0, 1)

    # Estimate monthly pipeline minutes based on average activity (e.g. 40 deploys/month)
    deploys_count = len(deployment_durations_seconds)
    avg_minutes_per_deploy = (total_deploy_minutes / deploys_count) if deploys_count > 0 else 0.8
    projected_monthly_runs = max(deploys_count * 4, 30)  # estimate monthly runs
    projected_monthly_minutes = round(projected_monthly_runs * avg_minutes_per_deploy, 1)

    # Calculate GitHub Actions cost
    billable_minutes = max(0.0, projected_monthly_minutes - GITHUB_FREE_MINUTES_LIMIT)
    actions_cost = round(billable_minutes * GITHUB_ACTIONS_LINUX_COST_PER_MIN, 2)

    # Cloud hosting cost
    hosting_cost = RENDER_INSTANCE_PRICING.get(instance_tier.lower(), 0.0)

    # Storage cost (GHCR)
    total_storage_mb = container_image_size_mb * images_stored_count
    total_storage_gb = total_storage_mb / 1024.0
    billable_storage_gb = max(0.0, total_storage_gb - 0.5)  # 500MB free
    storage_cost = round(billable_storage_gb * GHCR_COST_PER_GB, 2)

    total_monthly_cost = round(actions_cost + hosting_cost + storage_cost, 2)

    # Actionable cost-reduction recommendations
    recommendations = []
    if instance_tier.lower() == "free":
        recommendations.append({
            "title": "Zero Cloud Hosting Bill",
            "impact": "Free",
            "suggestion": "Running on Render free tier ($0/mo). Instance spins down after 15 minutes of inactivity.",
        })
    else:
        recommendations.append({
            "title": "Instance Rightsizing",
            "impact": "Save up to $18/mo",
            "suggestion": "Evaluate CPU and memory metrics on /metrics before upgrading beyond Starter tier ($7/mo).",
        })

    if container_image_size_mb > 150:
        recommendations.append({
            "title": "Multi-Stage Docker Optimization",
            "impact": "Reduce GHCR Storage & Speed Up Deploys",
            "suggestion": f"Container image is {container_image_size_mb} MB. Using multi-stage builds or stripping build caches can reduce image size to under 90 MB.",
        })

    recommendations.append({
        "title": "Pipeline Dependency Caching",
        "impact": "Save 25-35s per build",
        "suggestion": "Add actions/cache for pip dependencies in pipeline.yml to avoid redownloading wheels on every commit.",
    })

    return {
        "projected_monthly_cost_usd": total_monthly_cost,
        "breakdown": {
            "github_actions_cost_usd": actions_cost,
            "hosting_cost_usd": hosting_cost,
            "container_storage_cost_usd": storage_cost,
        },
        "metrics": {
            "total_deploy_minutes": total_deploy_minutes,
            "projected_monthly_minutes": projected_monthly_minutes,
            "free_minutes_remaining": max(0.0, GITHUB_FREE_MINUTES_LIMIT - projected_monthly_minutes),
            "container_image_size_mb": container_image_size_mb,
            "images_stored_count": images_stored_count,
            "instance_tier": instance_tier,
        },
        "recommendations": recommendations,
    }

