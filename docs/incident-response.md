# Incident response

## Steps
1. Confirm: open `<SERVICE_URL>/health` and `/version`. Check the Render logs and UptimeRobot.
2. Decide: is the service **down**, or is a **bad release live but healthy**?
3. Down: wait for Render's automatic restart. If it stays down, redeploy the last good SHA with the rollback workflow.
4. Bad release: run **Actions, then rollback, then Run workflow** with the last good full 40-character SHA.
5. Confirm `/version` shows the old SHA.
6. **Open a revert or fix pull request** so `main` no longer contains the bad code. Rolling back production does not change Git history.
7. Fill in the record below.

**Restart and recovery note:** Render may need to pull the deployed image again after a restart, rescheduling, or scaling. Keep every rollback image available in GHCR and check `/version` after recovery. Do not select **Manual Deploy → Deploy latest reference** after a rollback unless intentionally returning to the service's configured tag. A subsequent normal pipeline deployment will still deploy the latest code on `main`, so create the revert/fix pull request promptly.

## Record
| Field | Notes |
|---|---|
| Failure time | |
| Symptoms | |
| Logs / evidence | |
| Root cause | |
| Fix | |
| Prevention | |
