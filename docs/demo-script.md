# Demo script (about 5 minutes)

**Before:** open the live URL a few minutes early (free services spin down after 15 minutes idle). Have screenshots and `docker compose up` ready as backup. Start Scenario A early, because alerts take 10 to 15 minutes.

## Main flow
1. Show the architecture diagram (`docs/architecture.md`).
2. Create a feature branch, change something small, open a pull request.
3. Show the `test` and `build-scan-publish` checks passing.
4. Merge. Show test, build-scan-publish, deploy-and-verify running in order.
5. Open `/dashboard` and `/version`: the new SHA is live.
6. Run Scenario B. Then show Scenario A's alert evidence.
7. Summarize: automation, reproducibility, security, observability, rollback, low cost.

## Scenario A: availability failure
Suspend the service in the Render dashboard. Show the UptimeRobot down alert and the logs. Resume it. Show the recovery alert.

## Scenario B: bad but healthy release
1. Merge a change where `/` returns a wrong message but `/health` still returns 200.
2. Run the rollback workflow with the previous good SHA.
3. Show `/version` and `/` back to the old behavior. Do not restart the service meanwhile.
4. Open a revert pull request and explain that rollback does not change Git history.

If a new deployment fails its health check, Render cancels it and keeps the old version running. That is health-gated deploys, not rollback.
