# Zenith AI

Zenith AI is a **multi-tenant personal chief-of-staff** web application: users sign in with **Google OAuth (PKCE)**, receive a **session JWT**, and interact through **natural-language chat** while the backend orchestrates **Google Calendar, Gmail, Tasks, Drive-backed notes**, and **Vertex AI (Gemini)** on **Google Cloud Platform**.

This document is structured for **operators, security reviewers, and AI-assisted tooling** (clear boundaries, flows, and assumptions).

---

## 1. Business context and product vertical

- **Vertical:** Productivity / executive assistant for knowledge workers.
- **Core promise:** One conversational surface to plan the day, triage email, manage tasks, and capture notes—grounded in the user’s real Google Workspace data.
- **Differentiators:** Multi-step agent pipeline (context → decomposition → synthesis), optional image attachments in chat, and Firestore-backed session memory.

---

## 2. Architecture (how it fits together)

| Layer | Responsibility |
|--------|------------------|
| **React SPA** (`frontend/`) | Auth token storage, chat UI, feature panels, React Query data fetching. |
| **FastAPI** (`main.py`) | REST + multipart chat, OAuth callback, JWT auth, rate limits, static SPA hosting. |
| **Agents** (`agents/`) | Zenith orchestration, Vertex AI calls, intent routing. |
| **Tools** (`tools/`) | Google APIs (Calendar, Gmail, Tasks, Drive) using per-user OAuth tokens from Firestore. |
| **Memory** (`memory/`) | Firestore user profiles, credentials, conversations, notes metadata. |

High-level flow:

1. User opens SPA → `GET /auth/login` → redirect to Google with **PKCE** + `state`.
2. Google → `GET /auth/callback` → token exchange → user upsert in Firestore → **JWT** issued → redirect to SPA with token in URL fragment (see **Security model**).
3. SPA calls APIs with `Authorization: Bearer <jwt>`.
4. Chat requests hit `POST /chat` (FormData + optional images) → agents/tools → JSON response.

---

## 3. End-to-end authentication and session flow

1. **Login:** `GET /auth/login` returns `{ authorization_url, state }`. The server stores the PKCE verifier keyed by `state` (Firestore with in-memory fallback).
2. **Callback:** `GET /auth/callback` validates `code`/`state`, exchanges the code, loads Google profile, upserts the user, mints JWT (`auth/dependencies.py`).
3. **Redirect allowlist:** `FRONTEND_REDIRECT_URLS` and `resolve_frontend_redirect_url()` prevent open redirects.
4. **Client:** SPA reads fragment params, stores JWT in `localStorage`, clears the URL (see `AuthContext.tsx`).
5. **API access:** `HTTPBearer` + `verify_token()` on protected routes; optional `check_rate_limit` for heavy routes.

---

## 4. Security model (assumptions and controls)

**Trust boundaries**

- **Browser:** Holds short-lived JWT; treat XSS as credential compromise (see mitigations below).
- **Cloud Run / backend:** Trusts Google token endpoint and Firestore; must not log secrets.

**Controls implemented**

- **OAuth:** PKCE, UUIDv4-shaped `state`, validation of callback query parameters (`auth/oauth_callback.py`), handling of Google `error=` (e.g. `access_denied`), hashed `state` fingerprints in logs instead of raw values.
- **JWT:** HS256, configurable expiry; failed verification logs a **reason code**, not token material.
- **Errors:** JSON errors use a stable shape (`detail`, `code`, `error`); unhandled exceptions return a **generic** message unless `DEBUG=true` (`api_errors.py`).
- **Chat errors:** Server does not return raw exception strings from `/chat`.
- **Firestore:** Transient gRPC errors retried with bounded backoff (`memory/firestore_client.py`).
- **User reads:** Short TTL cache for `get_user_by_id` with invalidation on writes (`memory/user_store.py`).
- **Audit:** `log_audit_event()` for security-relevant events (e.g. successful OAuth) without credential fields (`auth/audit.py`).
- **Frontend:** React Markdown uses **rehype-sanitize**; Gmail HTML uses **DOMPurify** + **strict iframe sandbox**; API client truncates/normalizes error text; **error boundary** wraps the app; chat list **virtualized** for performance at scale.

**Operator assumptions**

- Secrets (`JWT_SECRET_KEY`, `GOOGLE_CLIENT_*`) live in **Secret Manager** or secure env—not in git.
- **CORS** and **FRONTEND_REDIRECT_URLS** match real deployment origins.
- Firestore **composite indexes** are deployed when queries require them (`firestore.indexes.json` placeholder included).

---

## 5. Features and primary API surface

| Area | Examples |
|------|-----------|
| **Auth** | `GET /auth/login`, `GET /auth/callback`, `GET /auth/me` |
| **Chat** | `POST /chat`, `POST /chat/stream` |
| **Workspace** | Calendar, Gmail, Tasks, Notes routes under `/calendar`, `/gmail`, `/tasks`, `/notes` |
| **Sessions** | `GET /sessions`, `POST /sessions`, `GET /chat/sessions/{id}`, `DELETE /sessions/{id}` |
| **Briefing** | `GET /agent/briefing` |
| **System** | `GET /health`, OpenAPI at `/docs` |

Full route list: run the backend and open **`/docs`**.

---

## 6. Local development

```bash
cd zenith
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
copy .env.example .env          # configure GCP + OAuth + JWT
uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd zenith/frontend
npm install
npm run dev
```

Vite proxies API paths to `http://localhost:8000` (see `vite.config.ts`).

---

## 7. Testing

**Backend (pytest)** — from `zenith/`:

```bash
pytest -q
```

Includes OAuth callback validation tests and lightweight HTTP API smoke tests (`conftest.py` sets dummy env vars).

**Frontend (Vitest)** — from `zenith/frontend`:

```bash
npm test
```

---

## 8. Deployment notes (Cloud Run)

- Container entrypoint: `Dockerfile` in `zenith/`.
- Set **`FRONTEND_REDIRECT_URLS`**, **`ALLOWED_ORIGINS`**, **`OAUTH_REDIRECT_URI`** to production URLs.
- Ensure OAuth consent screen and redirect URIs match Cloud Run hostname.
- Use **Workload Identity** or service account JSON appropriately for Vertex + Firestore.

---

## 9. Accessibility and UX

- Prefer **`focus-visible`** rings on primary buttons (`GlassButton`, quick actions).
- Chat log region uses `role="log"` / `aria-live` for assistive technologies.
- Settings drawer exposes `role="dialog"` and labelled close control.
- Virtualized chat history reduces DOM size for long sessions (`@tanstack/react-virtual`).

---

## 10. Project layout (abridged)

```
zenith/
  main.py
  config.py
  api_errors.py
  auth/
  agents/
  tools/
  memory/
  models/
  frontend/           # Vite + React SPA
  firestore.indexes.json
```

---

## 11. License

MIT
