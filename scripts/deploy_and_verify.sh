#!/usr/bin/env bash
# Deploys one exact image tag to Render, then waits until /version shows that SHA.
# Usage: IMAGE=ghcr.io/owner/deployeasy SHA=<commit sha> \
#        RENDER_DEPLOY_HOOK_URL=... SERVICE_URL=... ./scripts/deploy_and_verify.sh
set -euo pipefail
: "${IMAGE:?}" "${SHA:?}" "${RENDER_DEPLOY_HOOK_URL:?}" "${SERVICE_URL:?}"
SERVICE_URL="${SERVICE_URL%/}"

echo "::group::Deploy"
ENCODED=$(python3 -c "import os,urllib.parse;print(urllib.parse.quote(os.environ['IMAGE']+':'+os.environ['SHA'],safe=''))")
SEP="&"
if [[ "$RENDER_DEPLOY_HOOK_URL" != *"?"* ]]; then
  SEP="?"
fi
# The hook URL is a secret: never echo it
curl -fsS -X POST --max-time 30 "${RENDER_DEPLOY_HOOK_URL}${SEP}imgURL=${ENCODED}" -o /dev/null
echo "Deploy requested for ${IMAGE}:${SHA}"
echo "::endgroup::"

echo "::group::Smoke test"
# Free Render services can take minutes to start, so retry for up to 10 minutes
for i in $(seq 1 30); do
  LIVE=$(curl -fsS --max-time 15 "${SERVICE_URL}/version" 2>/dev/null \
    | python3 -c "import sys,json;print(json.load(sys.stdin).get('git_sha',''))" 2>/dev/null || true)
  if [ "$LIVE" = "$SHA" ]; then echo "Live version matches ${SHA}"; break; fi
  echo "Attempt ${i}/30: live version is '${LIVE:-unreachable}', waiting..."
  sleep 20
done
[ "$LIVE" = "$SHA" ] || { echo "::error::Timed out waiting for ${SHA} to go live"; exit 1; }
curl -fsS --max-time 15 "${SERVICE_URL}/health"; echo
echo "::endgroup::"
