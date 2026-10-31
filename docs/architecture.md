# Architecture

```mermaid
flowchart TD
  Dev[Developer] -->|pull request| GH[GitHub]
  GH --> CI[test: Ruff, pytest, Gitleaks]
  CI -->|merge to main| B[build-scan-publish: build once, Trivy scan]
  B -->|push SHA tag| GHCR[(GHCR registry)]
  GHCR --> D[deploy-and-verify]
  D -->|deploy hook + imgURL| R[Render service]
  D -->|poll /version for SHA| R
  U[UptimeRobot] -->|/health every 5 min| R
  U -->|email alert| Team
```

| Piece | Detail |
|---|---|
| App | FastAPI, one worker, port from `PORT` (default 8080) |
| Image | `ghcr.io/<owner>/deployeasy:<commit-sha>` (also `latest`) |
| Secrets | `RENDER_DEPLOY_HOOK_URL` (GitHub secret). `SERVICE_URL` (GitHub variable, not secret) |
| Triggers | Pull request: `test` + build and scan only. Push to `main`: full pipeline. Manual: `rollback.yml` |
| Safety | `production-deploy` concurrency group, so deployments never overlap |
