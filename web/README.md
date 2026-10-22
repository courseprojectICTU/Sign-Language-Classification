# US-022 — Upload/capture frontend

Static HTML/CSS/JavaScript for the signed-off architecture (Cloudflare Pages frontend,
Google Cloud Run Python backend). Browser **sends an image**, not raw 93 landmarks.
Server must handle MediaPipe and the 93-value pipeline, including a horizontal flip
matching the realtime notebook where appropriate.

## Run locally

Create `web/config.js` containing `window.VSL_API_BASE = "http://localhost:8000";`.
Insert `<script src="./config.js"></script>` before `app.js` in `index.html`
for local development, or generate it in deployment. Serve `web/` over
`localhost` (e.g. `python -m http.server 5500 --directory web`).

**Important:** `web/config.js` is local/deploy config. Never commit credentials.
The current index.html does not load config.js until included; see deployment
instructions above. A follow-up PR may add a public non-secret config template
and automate environment-specific config during Cloudflare deployment.

API contract (see `docs/KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md`):
POST /predict multipart field `file` with JPEG/PNG; response has `status`,
`letter`, `confidence` in range 0..1, `top_k`, `model_version`.
Statuses `no_hand` and `no_face` are handled. Backend CORS must permit
local development and the deployed Cloudflare Pages domain.

No live API deployment or real camera/browser test is claimed by this PR.
