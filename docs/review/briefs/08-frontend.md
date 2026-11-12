# Brief 08: frontend

You review the browser side of sign-in, accounts and the contribution pipeline: what it shows, what it trusts, what it keeps. Review only: you find and prove problems, you do not fix them.

## Before you start

1. Read `CLAUDE.md`, then `docs/review/README.md`, package 08 in `docs/review/review-plan.md` with the suspicions it names (S8, S11), and `docs/review/findings/README.md`.
2. Read `docs/auth.md` (the frontend part) and `docs/design-system.md` (only to know the words of the UI).
3. Run `echo $WT_BRANCH $BACKEND_PORT $FRONTEND_PORT $DB_NAME`. The servers already run. Do not start them again.

## Files

- `frontend/src/router/index.ts`, `frontend/src/router/guards.ts`.
- `frontend/src/stores/auth.ts`, `stores/features.ts`, `stores/contribution.ts`, `stores/curation.ts`, `stores/admin.ts`.
- `frontend/src/plugins/axios.ts`, `plugins/gtag.ts`.
- `frontend/src/views/`: `LoginView.vue`, `LoginVerifyView.vue`, `AccountView.vue`, `AdminView.vue`, `ForbiddenView.vue`, `ContributeView.vue`, `CurationQueueView.vue`, `CurationReviewView.vue`.
- Every `v-html`: `components/commons/UnitTableRow.vue` (lines 45, 47), `components/commons/tools/ToolSlider.vue` (line 68), `components/contribute/ContributionGuide.vue` (231, 268), `components/curation/ReviewThread.vue`.
- `frontend/nginx.conf`, `frontend/nginx-security-headers.conf`, `frontend/index.html`.
- `frontend/src/utils/localStorage.ts`, `utils/cookieConsent.ts`.

## Questions

1. `v-html`. For each one, where does the HTML come from? `UnitTableRow.vue` and `ToolSlider.vue` have no DOMPurify. Can any text there come from a user, from the data repo (a dictionary `symbol` or `unit` sent by a contributor), or from a URL? If yes, it is a stored XSS. Prove it with a spec that mounts the component with `<img src=x onerror=...>`.
2. DOMPurify. `ContributionGuide.vue` and `ReviewThread.vue`: which config? Are links forced to `rel="noopener noreferrer"`? Are images from any host allowed? Is `symbolHtml` safe for any input?
3. Redirects. `LoginView.vue` and `LoginVerifyView.vue` read `next`. `AccountView.vue` reads `next` after the ORCID add-email step. `ForbiddenView.vue` reads `next` and `need`. Can any of them send the user to another site, or show text from the URL as HTML?
4. Features fail-open. `stores/features.ts` turns contributions on when `GET /features` fails. What does a user see when the backend is down and the flag is off on prod: links to pages that answer 404? Is this what we want? (S11)
5. CSP. `nginx-security-headers.conf` sends `Content-Security-Policy-Report-Only`. List what would break if it became enforcing: inline styles, Vuetify, ECharts, Google Analytics, the CDN for SEM images, `data:` and `blob:` URLs, the worker of the tar builder. Check `index.html` for inline scripts. Use Claude in Chrome on `http://localhost:$FRONTEND_PORT/` and read the console for CSP reports. (S8)
6. Other headers. HSTS, `X-Frame-Options` or `frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`, `X-Content-Type-Options`. Which ones are sent by `nginx.conf`, and which are left to the ingress? Is the `Referrer-Policy` strict enough that a sign-in link with a token never goes to a third party in `Referer`?
7. Storage. What goes into `localStorage` and `sessionStorage`: drafts, role, address, tokens? What stays after sign-out? On a shared computer at the workshop, can the next person see the draft or the address of the previous one?
8. Sign-out. Does the frontend clear its stores (auth, contribution, curation, admin)? Does a second tab notice the sign-out?
9. Error messages. For each `auth.errors.*` and `admin.errors.*` key in `locales/en.json`, find the code that shows it. Is any key never used? Is any backend error code shown as raw text because no key matches? Is every key also in `fr.json`, with accents?
10. Hardcoded values. Links to the data repo, to GitHub, to the ORCID host, to `epfl.ch`. Do they follow the environment, or point to the real repo from dev and stage?
11. Guard and backend disagree. Is there a page that the guard opens but whose first API call answers 401 or 403? What does the user see then?

## Method

1. Read the router and the guard first, then each view.
2. For each question, make the smallest proof:
   - First choice: a Vitest spec in a new file next to the component, `__tests__/review-08-<topic>.spec.ts`, with `it.fails(...)` so it fails until the fix. Look at `frontend/src/views/__tests__/ContributeView.spec.ts` for the mount setup (Vuetify, i18n, Pinia).
   - Second choice: a Claude in Chrome check on `http://localhost:$FRONTEND_PORT/`, with a screenshot or the console text in the finding. Sign in with the code from `.wt-logs/backend.log` (use `tail -n 50`).
   - For headers: `fetch('/', {method: 'HEAD'})` from the page. In dev, Vite serves the page, not nginx, so the headers of `nginx-security-headers.conf` are not there: read the file for those.
3. Run your specs with `cd frontend && pnpm run test:unit <file>`.

## Rules

- Review only. Do not change application code. You add only test files that prove a finding, and your findings file.
- A finding needs a file and line, and a proof.
- Send requests only to your own servers, with Claude in Chrome on the ports of your worktree. Never to stage, prod or any `epfl.ch` host.
- Do not post anything on GitHub.
- In the browser, do not click a button that opens a `confirm()` or `alert()` dialog: it blocks the browser tool.
- Give each finding a severity from the scale in `docs/review/README.md`.
- Write in simple English. No em dash.

## Output

- `docs/review/findings/08-frontend.md`, from the template. One section per question.
- The spec files.
- Commit on your branch with explicit paths: `docs(review): findings of package 08`. Do not open a pull request. Say when you are done.
