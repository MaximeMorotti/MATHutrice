# MATHutrice

LLM-based tutor that helps EPF first-year students practise mathematical tools through notions, competences and training.

Students sign in, pick a module (for example *Trigonométrie*), see their progression on the competences it evaluates, train on generated exercises (multiple-choice and open-answer questions), and ask a chat tutor for help. Teachers upload course PDFs that the tutor draws on. Admins can **impersonate** a user to see the application as they do.

The application is a single FastAPI app (`mathutrice/app.py`) rendering Jinja templates. Every LLM call goes through one OpenAI-compatible **LLM endpoint** ([ADR 0002](docs/adr/0002-openai-compatible-llm-client.md)). The vocabulary used here is defined in [`CONTEXT.md`](CONTEXT.md).

## Run it locally

### Requirements

- Python **3.14** (the exact version is in `.python-version`).
- [uv](https://docs.astral.sh/uv/), which installs that Python version and the locked dependencies from `uv.lock`. If `uv sync` reports `No interpreter found for Python 3.14.7`, your uv predates that release: run `uv self update`.
- A key for an LLM endpoint. The default endpoint is Mistral: get a key at <https://console.mistral.ai> (a free account works).

No Microsoft Entra ID credentials are needed: a local clone signs in with the **connexion de développement** (see below).

### Install and start

```sh
git clone -b course-2026 <your fork URL> mathutrice
cd mathutrice
uv sync
. .venv/bin/activate          # Windows: .venv\Scripts\activate
cp .env.example .env          # then set LLM_API_KEY in .env
uvicorn mathutrice.app:app --port 8000
```

Open <http://localhost:8000/>. You are sent to the **connexion de développement** page, where you choose an email address and a role. The SQLite database (`mathutrice.db`) is created on first start.

To check that a fresh clone really runs, follow the [smoke test](docs/smoke-test.md).

## Configuration

Settings are read from the environment, and from `.env` at the repository root. [`.env.example`](.env.example) lists every variable the application reads, with its default for a local clone. The application refuses to start when a required one is missing or empty.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LLM_BASE_URL` | yes | OpenAI-compatible LLM endpoint. `.env.example` points at Mistral. |
| `LLM_MODEL` | yes | Model served by that endpoint. |
| `LLM_API_KEY` | yes | Key for that endpoint. Never commit it. |
| `DATABASE_URL` | yes | SQLAlchemy URL. SQLite locally; PostgreSQL on deployed environments (`postgresql+psycopg2://user:password@host:5432/mathutrice`). |
| `SESSION_SECRET` | yes | Signing key for session cookies. See [the caveat below](#session_secret-caveat). |
| `AUTH_MODE` | no | `entra` (default) or `dev`. Case and surrounding spaces are ignored; any other value stops startup. |
| `DEV_LOGIN_KEY` | no | Shared key required by every dev sign-in. Only used when `AUTH_MODE=dev`. |
| `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` | when `AUTH_MODE=entra` | Microsoft Entra ID app registration. |
| `REDIRECT_URL` | when `AUTH_MODE=entra` | Entra redirect URI of this deployment, ending in `/auth`, e.g. `https://example.org/auth`. It must be registered on the Entra app. |
| `POST_LOGOUT_REDIRECT_URL` | when `AUTH_MODE=entra` | Where Entra sends the user after logout, e.g. `https://example.org/test_login`. |

To use another LLM endpoint (for example the self-hosted gateway), change `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` together.

## Authentication

`AUTH_MODE` selects how users sign in.

- **`entra`** (the default when `AUTH_MODE` is unset): sign-in through Microsoft Entra ID. Only `@epf.fr` and `@epfedu.fr` addresses are accepted. This is the only mode for production.
- **`dev`**: the **connexion de développement**. You pick an email address and a role (Student, Teacher or Admin) and are signed in as that user, **with no proof of identity**. It needs no Entra configuration and no pre-existing user. `.env.example` sets this mode so that a clone runs out of the box.

The connexion de développement is not **impersonation**: impersonation is an Admin who really signed in viewing the application as another user. It works the same in both modes.

### Connexion de développement (`AUTH_MODE=dev`)

In this mode:

- Startup prints a `WARNING: AUTH_MODE=dev` line saying whether `DEV_LOGIN_KEY` is set.
- Every page of the application, apart from the sign-in page itself, shows a red banner with the current email and role, and a *Changer d'utilisateur* link. Without `DEV_LOGIN_KEY`, the banner also says access is open to everyone.
- `GET /dev/login` lists the existing users grouped by role, each with a one-click sign-in button, and a form to sign in as any email from an allowed domain with the role you choose. `/test_login` redirects there.
- Switching user is signing in again: the new sign-in replaces the session.
- `/logout` clears the session and goes back to `/`, with no Microsoft logout.
- Session cookies are not marked `Secure`, so sign-in works over `http://localhost`.
- The Entra callback (`/auth`) does not exist.

In `entra` mode, `/dev/login` does not exist, and a `DEV_LOGIN_KEY` left set is ignored with a warning.

#### `DEV_LOGIN_KEY`

Unset or empty, anyone who can reach the application can sign in as anyone, Admin included. That is fine on `localhost`. On a publicly reachable fork, set `DEV_LOGIN_KEY` to keep casual visitors out: the sign-in page then shows a key field, and every sign-in must provide the key.

#### `SESSION_SECRET` caveat

`DEV_LOGIN_KEY` only guards the sign-in form. The session itself is a cookie signed with `SESSION_SECRET`. With the placeholder value from `.env.example`, which is public, **anyone can forge a session cookie for any user and role and skip `DEV_LOGIN_KEY` entirely**. On any deployed environment, set `SESSION_SECRET` to a random secret, for example:

```sh
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Even then, the key is a speed bump for a fork, not real authentication.

#### Scripted connexion de développement

`POST /dev/login` takes form fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `email` | yes | Must end in `@epf.fr` or `@epfedu.fr`. The user is created if it does not exist. |
| `name` | no | Display name. Defaults to the stored name, or for a new user to one built from the email (`bob.leponge` → *Bob Leponge*). A stored name is never overwritten in the database, but the session uses the submitted name. |
| `role` | no | `Student`, `Teacher` or `Admin`, case-insensitive. Saved on the user. Without it, an existing user keeps their role and a new user becomes Student. |
| `key` | when `DEV_LOGIN_KEY` is set | The shared key. |

A successful sign-in answers `303` with the session cookie, redirecting to `/teacher` for a Teacher or Admin and to `/` for a Student. Failures answer `401` for a wrong or missing key, `403` for an email outside the allowed domains, and `400` for an invalid role.

With `curl`, keep the session cookie in a cookie jar (`-c` writes it, `-b` sends it back):

```sh
# Sign in as a Teacher; prints 303 on success.
curl -s -o /dev/null -w '%{http_code}\n' -c cookies.txt \
  -d email=bob.leponge@epf.fr -d name='Bob Leponge' -d role=Teacher -d key="$DEV_LOGIN_KEY" \
  http://localhost:8000/dev/login

# Later requests act as that user.
curl -s -b cookies.txt -c cookies.txt http://localhost:8000/teacher
```

The session expires after one hour without a request.

## Deployment checklist

Before deploying the real EPF environment:

- [ ] `AUTH_MODE` non défini ou `entra`.
- [ ] `CLIENT_ID`, `CLIENT_SECRET` and `TENANT_ID` set for the Entra app registration.
- [ ] `REDIRECT_URL` and `POST_LOGOUT_REDIRECT_URL` set to this deployment's URLs, and `REDIRECT_URL` registered on the Entra app.
- [ ] `SESSION_SECRET` set to a random secret, not the placeholder from `.env.example`.
- [ ] `DATABASE_URL` pointing at PostgreSQL.
- [ ] `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` set, and the key not committed.
- [ ] The application served over HTTPS: in `entra` mode, session cookies are `Secure` and are not sent over plain HTTP.

A course fork deployed with `AUTH_MODE=dev` must set `DEV_LOGIN_KEY` and a random `SESSION_SECRET`.

## Development

- Package boundaries are machine-checked: see [`mathutrice/README.md`](mathutrice/README.md).
- Architecture decisions are recorded in [`docs/adr/`](docs/adr/).
- Issues are tracked in [GitHub Issues](https://github.com/EPF-MDE/MATHutrice/issues).

## License

[MIT](LICENSE)
