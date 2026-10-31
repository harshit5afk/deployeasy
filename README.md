# DeployEasy

An automated CI/CD pipeline with health verification, monitoring, rollback, and a live status dashboard. Push code, and it is tested, built into a Docker image once, scanned, published, deployed to Render, and verified automatically.

![pipeline](https://github.com/<owner>/deployeasy/actions/workflows/pipeline.yml/badge.svg)

**Live URL:** `<add your Render URL here>`  |  Dashboard: `<url>/dashboard`

## Endpoints
| Path | Purpose |
|---|---|
| `/` | Welcome message |
| `/health` | Basic availability (used by Docker, Render, UptimeRobot) |
| `/version` | App version and Git commit SHA of the running image |
| `/metrics` | Process uptime and requests since process start (reset on restart) |
| `/dashboard` | Read-only status page |

## Run locally
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest && ruff check .
uvicorn app.main:app --port 8080          # or: docker compose up --build
```

## Pipeline (`.github/workflows/pipeline.yml`)
`test` (Ruff, pytest, Gitleaks) then `build-scan-publish` (one build, Trivy scan, push to GHCR on main) then `deploy-and-verify` (Render deploy hook, wait for the new SHA on `/version`, check `/health`). Pull requests never publish or deploy. Rollback: **Actions, then rollback, then Run workflow** with a previous full commit SHA.

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
- Never commit secrets. Dependabot keeps Python packages, Actions, and the base image updated. Pin action versions to commit SHAs for extra supply-chain safety.
