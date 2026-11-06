# DeployEasy

An automated CI/CD pipeline with health verification, monitoring, rollback, and a live status dashboard. Push code, and it is tested, built into a Docker image once, scanned, published, deployed to Render, and verified automatically.

![pipeline](https://github.com/harshit5afk/deployeasy/actions/workflows/pipeline.yml/badge.svg)

**Live URL:** `<add your Render URL here>`  |  Dashboard: `<url>/dashboard`

## Endpoints
| Path | Purpose |
|---|---|
| `/` | Developer-first marketing & product landing page |
| `/login` / `/signup` | Sign in & instant demo developer access |
| `/dashboard` | Multi-view deployment observatory & control center |
| `/health` | Basic availability (used by Docker, Render, UptimeRobot) |
| `/version` | App version and Git commit SHA of the running image |
| `/metrics` | Process uptime and requests since process start (reset on restart) |
| `/api/overview` | Aggregated system metrics, fleet health, uptime, and deployment activity |
| `/api/projects` | Connected repositories and microservice projects |
| `/api/projects/{id}/deployments` | Historical deployment logs, status badges, and duration metrics |
| `/api/deployments/{id}/diff` | Release comparison and commit jump between deployments |
| `/api/deployments/trigger` | Trigger manual release deployment for a specific commit SHA |
| `/api/deployments/rollback` | Instant one-click production rollback to a previous image tag |
| `/api/projects/{id}/readiness` | 0-100% Pre-deploy readiness score & 5-point release gate audit |
| `/api/analyze-logs` | Intelligent deployment failure log diagnostic engine |
| `/api/validate-env` | Environment variable syntax, placeholder, and protocol validator |
| `/api/projects/{id}/check-health` | On-demand live health check probe with response time tracking |
| `/api/projects/{id}/security` | Trivy container vulnerability reports and Gitleaks secrets audit status |
| `/api/auth/demo-login` & `/me` | Quick demo authentication and session identity |
| `/api/runs` | Recent GitHub Actions workflow runs (cached for 60s) |

## Run locally

```bash
# Option 1: Using npm scripts (Quick start)
npm start             # Starts server with auto-reload on http://localhost:8080
npm test              # Runs the complete pytest suite
npm run lint          # Runs Ruff linter

# Option 2: Using Python directly
pip install -r requirements.txt -r requirements-dev.txt
pytest && ruff check .
uvicorn app.main:app --port 8080 --reload     # or: docker compose up --build
```

## Pipeline (`.github/workflows/pipeline.yml`)
`test` (Ruff, pytest, Gitleaks) then `build-scan-publish` (one build, Trivy scan, push to GHCR on main) then `deploy-and-verify` (Render deploy hook, wait for the new SHA on `/version`, check `/health`). Pull requests never publish or deploy. Rollback: **Actions, then rollback, then Run workflow** with a previous full commit SHA, or trigger directly from the DeployEasy dashboard with one click. Workflows pin action references to exact commit SHAs for supply chain safety.

## One-time setup (do in this order)
1. Create the **public** GitHub repo `deployeasy`, push this code, enable branch protection on `main` and secret scanning.
2. Merge to `main`. The first image is published to GHCR (the deploy job is skipped because `SERVICE_URL` is not set yet).
3. In GitHub **Packages**, set the `deployeasy` package visibility to **public**.
4. In Render, create a web service from an **existing image**: `ghcr.io/<lowercase-owner>/deployeasy:latest`. Health check path `/health`. Confirm the free instance type is offered for image-backed services.
5. Copy the service's **deploy hook URL**. In GitHub, **Settings, Secrets and variables, Actions**: add secret `RENDER_DEPLOY_HOOK_URL` and variable `SERVICE_URL` (the Render URL).
6. Optional dashboard runs: set `GITHUB_REPO=<owner>/deployeasy` in Render's environment variables.
7. Add an UptimeRobot monitor on `<SERVICE_URL>/health` (email alerts for down and up, after consecutive failures).
8. Merge a small change and confirm the full pipeline goes green.

## Docs
[Architecture](docs/architecture.md) | [Incident response](docs/incident-response.md) | [Demo script](docs/demo-script.md)

## Screenshots

> Capture these before the demo as backup evidence:
> - Passing pipeline run (all three jobs green)
> - GHCR image list showing SHA-tagged images
> - Live URL showing `/version` with the deployed SHA
> - UptimeRobot dashboard showing the monitor as "Up"
> - A fired down-alert email and a recovery-alert email
> - A successful rollback workflow run and its revert pull request

## Notes
- Render free services spin down after 15 minutes idle and can take about a minute to wake. The smoke test retries for up to 10 minutes.
- Never commit secrets. Dependabot keeps Python packages, Actions, and the base image updated. Action versions are pinned to commit SHAs for extra supply-chain safety.
