# Brief 09: deploy and config

You review how the Hub runs on the cluster: ingress, headers, forwarded IP, secrets, replicas, images, dependencies. Pierre owns this package. Your part is the reading. You only read the k8s config, you never change it. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 09 in `docs/review/review-plan.md` with the suspicions it names (B1, B2, B7, B8, S8), and `docs/review/findings/README.md`.
2. Read `docs/releasing.md` and `backend/README.md` (the parts about deploy, upload and backup).
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## Files

- The k8s config, read only: `~/code/enack8s-app-config/epfl-resslab/resslab-hub/` (`base/`, `overlays/dev`, `overlays/stage`, `overlays/prod`, `components/google-analytics`).
- `backend/resslab_hub/config.py` (`refuse_default_secrets`, every setting and its default).
- `backend/resslab_hub/main.py` (middleware order, `/docs`, `/openapi.json`, `ROOT_PATH`).
- `backend/resslab_hub/utils/rate_limit.py`.
- `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/nginx-security-headers.conf`.
- `backend/uv.lock`, `frontend/pnpm-lock.yaml`.
- `.github/workflows/` of this repo.

## Questions

1. Forwarded IP. The ingress is nginx, not Traefik (the comment in `rate_limit.py` says Traefik). The backend runs uvicorn with `FORWARDED_ALLOW_IPS=*` (check where it is set). Which address does `get_remote_address` return on the cluster: the client, the ingress pod, or a value the client can set in `X-Forwarded-For`? Read the ingress annotations and the uvicorn flags. If the client can set it, every per-IP limit is useless. If it is the ingress pod, the whole world shares one limit. (B2)
2. Limits per IP. List every limit with its key and value. Which ones will a room of 30 people on one network reach in the first hour of the workshop? (B1) Package 10 measures it, you give the list.
3. Body size and timeouts. What `proxy-body-size`, `proxy-read-timeout` and buffering does the ingress set? The backend allows 50 MB. Do the two agree? What does a user see when the ingress refuses first (an HTML 413 from nginx, not JSON)? (S8)
4. Headers at the edge. Does the ingress add HSTS, or rely on `nginx.conf` of the frontend? Does the `/api` route get any security header?
5. Public docs. Are `/api/docs`, `/api/redoc` and `/api/openapi.json` open on prod? What do they tell a stranger (every route, every field)? This is a decision for Pierre: write the facts.
6. Secrets. Which keys come from Infisical (`infisical-crd.yaml`), which are plain in the overlays? Is any secret, token or password in a plain ConfigMap or in this repo? Does `refuse_default_secrets` cover every key that matters (`GITHUB_APP_*`, `GITHUB_OAUTH_*`, `ORCID_*`, `SMTP_*`, the session secret if there is one)?
7. Prod config for the workshop. Make the table: each setting the pipeline needs (`CONTRIBUTIONS_ENABLED`, `PUBLIC_BASE_URL`, `DATA_REPO`, `DATA_REPO_REVIEWERS`, `MAX_OPEN_CONTRIBUTIONS`, `ADMIN_EMAILS`, `CONTRIBUTOR_DOMAINS`, `SMTP_*`, `GITHUB_OAUTH_*`, `GITHUB_APP_*`, `ORCID_*`, `SESSION_TTL_DAYS`, `LOGIN_CODE_TTL_MINUTES`), with its value on dev, stage and prod today, and what prod needs. (B7)
8. Replicas and work in the request. The backend is one replica. Validation and the GitHub calls run inside the request. How many workers does uvicorn run? Do the in-memory things (rate limiter, response cache, GitHub client) break with more replicas or more workers? (B8)
9. Images. Base images and their age, user (root or not), read-only file system, resource limits and requests in the deployments. Can the backend pod write to disk, and where do uploaded archives go?
10. Dependencies. Run `cd backend && uv run --with pip-audit pip-audit` if the network allows it, else list the packages that parse untrusted input (multipart, tar, CSV, markdown) and their versions. Run `cd frontend && pnpm audit --prod`. Report only what is reachable from the pipeline or sign-in.
11. CI and deploy. Can a pull request from a fork run a workflow with secrets? Who can push a `v*.*.*` tag (it deploys prod)? Is the release-please token scoped?
12. Backups. The nightly dump keeps the `auth_*` tables 30 days. Was a restore ever tested? Write the steps Pierre needs to test it once before the workshop.

## Method

1. Read the k8s config with `rg` and `cat`. Never `kubectl`, never `curl` a cluster host.
2. For each finding, quote the file and line of the config or the code.
3. Questions that need the live cluster (1 in part, 7, 12): write what Pierre must check, as "to check by Pierre", with the exact command (for example `kubectl -n <ns> exec deploy/resslab-hub-backend -- env | grep FORWARDED`). Pierre runs them.

## Rules

- Review only. Never write in `~/code/enack8s-app-config`. Do not change application code.
- Send requests only to your own servers, with `wtx curl`. Never to stage, prod or any `epfl.ch` host.
- Do not post anything on GitHub.
- Never copy a secret value into the findings, even a test one. Write the key name only.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/09-deploy-config.md`, from the template. The prod config table of question 7 near the top, then one section per question.
- Commit on your branch with explicit paths: `docs(review): findings of package 09`. Do not open a pull request. Say when you are done.
