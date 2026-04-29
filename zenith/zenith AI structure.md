# Zenith AI Structure & Architecture

This document outlines the architecture, end-to-end flows, and security model of Zenith AI.

## 1. Architecture (how it fits together)

| Layer | Responsibility |
|--------|------------------|
| **React SPA** (`frontend/`) | Auth token storage, chat UI, feature panels, React Query data fetching. |
| **FastAPI** (`main.py`) | REST + multipart chat, OAuth callback, JWT auth, rate limits, static SPA hosting. |
| **Agents** (`agents/`) | Zenith orchestration, Vertex AI calls, intent routing. |
| **Tools** (`tools/`) | Google APIs (Calendar, Gmail, Tasks, Drive) using per-user OAuth tokens from Firestore. |
| **Memory** (`memory/`) | Firestore user profiles, credentials, conversations, notes metadata. |

High-level flow:

1. User opens SPA → `GET /auth/login` → redirect to Google with **PKCE** + `state`.
2. Google → `GET /auth/callback` → token exchange → user upsert in Firestore → **JWT** issued → redirect to SPA with token in URL fragment.
3. SPA calls APIs with `Authorization: Bearer <jwt>`.
4. Chat requests hit `POST /chat` (FormData + optional images) → agents/tools → JSON response.

## 2. End-to-end authentication and session flow

1. **Login:** `GET /auth/login` returns `{ authorization_url, state }`. The server stores the PKCE verifier keyed by `state` (Firestore with in-memory fallback).
2. **Callback:** `GET /auth/callback` validates `code`/`state`, exchanges the code, loads Google profile, upserts the user, mints JWT (`auth/dependencies.py`).
3. **Redirect allowlist:** `FRONTEND_REDIRECT_URLS` and `resolve_frontend_redirect_url()` prevent open redirects.
4. **Client:** SPA reads fragment params, stores JWT in `localStorage`, clears the URL (see `AuthContext.tsx`).
5. **API access:** `HTTPBearer` + `verify_token()` on protected routes; optional `check_rate_limit` for heavy routes.

## 3. Security model (assumptions and controls)

**Trust boundaries**
- **Browser:** Holds short-lived JWT; treat XSS as credential compromise.
- **Cloud Run / backend:** Trusts Google token endpoint and Firestore; must not log secrets.

**Controls implemented**
- **OAuth:** PKCE, UUIDv4-shaped `state`, validation of callback query parameters (`auth/oauth_callback.py`), handling of Google `error=` (e.g. `access_denied`), hashed `state` fingerprints in logs instead of raw values.
- **JWT:** HS256, configurable expiry; failed verification logs a **reason code**, not token material.
- **Errors:** JSON errors use a stable shape (`detail`, `code`, `error`); unhandled exceptions return a **generic** message unless `DEBUG=true` (`api_errors.py`).
- **Chat errors:** Server does not return raw exception strings from `/chat`.
- **Firestore:** Transient gRPC errors retried with bounded backoff (`memory/firestore_client.py`).
- **User reads:** Short TTL cache for `get_user_by_id` with invalidation on writes (`memory/user_store.py`).
- **Audit:** `log_audit_event()` for security-relevant events without credential fields (`auth/audit.py`).
- **Frontend:** React Markdown uses **rehype-sanitize**; Gmail HTML uses **DOMPurify** + **strict iframe sandbox**; API client truncates/normalizes error text; **error boundary** wraps the app; chat list **virtualized** for performance at scale.

## 4. Features and primary API surface

| Area | Examples |
|------|-----------|
| **Auth** | `GET /auth/login`, `GET /auth/callback`, `GET /auth/me` |
| **Chat** | `POST /chat`, `POST /chat/stream` |
| **Workspace** | Calendar, Gmail, Tasks, Notes routes under `/calendar`, `/gmail`, `/tasks`, `/notes` |
| **Sessions** | `GET /sessions`, `POST /sessions`, `GET /chat/sessions/{id}`, `DELETE /sessions/{id}` |
| **Briefing** | `GET /agent/briefing` |
| **System** | `GET /health`, OpenAPI at `/docs` |

Full route list: run the backend and open **`/docs`**.

## 5. Project layout (abridged)

```text
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
