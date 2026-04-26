# Developer Setup Guide

Welcome to the **Montage Project**! This guide will help you set up the project for local development.

---

## Overview

The **Montage Project** is a web application with two main components:

1. **Frontend**:
   - Built with **Vue 3**.
   - Includes **Wikimedia Codex** for UI components, **Axios** for API requests, and **Pinia** for state management.
   - Compiled using **Vite** for fast builds.

2. **Backend**:
   - Built with **Clastic**, a Python framework.
   - Uses various Python libraries such as:
     - **SQLAlchemy**: Database interactions.
     - **mwoauth**: Used for authentication with MediaWiki's OAuth.
     - **pymysql**: MySQL driver.
   - Serves the frontend and exposes API endpoints for application functionality.

---

## Prerequisites

Ensure the following are installed:
- **Docker** and **Docker Compose**: [Install Docker](https://www.docker.com/products/docker-desktop).
- **Node.js** (v20 or above): [Install Node.js](https://nodejs.org).
- **Make**: Available on most Unix-based systems.

---

## Setting Up the Project

### 1. Clone the Repository
```bash
git clone git@github.com:hatnote/montage.git
cd montage
```

### 2. Set up the Frontend
```bash
cd frontend
npm install
```

### 3. Configure Environment Variables
```bash
cp .env.default .env
```

Edit the `.env` file to match your development environment. By default, it's configured to connect to a locally running backend at `http://localhost:5001`.

### 4. Authentication (OAuth)

Montage uses MediaWiki OAuth for authentication. There are two modes for local development:

**Default (dev/debug mode) -- no setup required:**
The backend runs with `debug: True` (the default in `config.default.yaml`). In this mode, the OAuth handshake is bypassed entirely and you are automatically logged in as `Slaporte`. This is sufficient for most frontend and backend development.

**Real OAuth (optional) -- for testing the actual login flow:**
If you need to test the real OAuth login/logout flow, you need to register an OAuth consumer:

1. Go to [Special:OAuthConsumerRegistration](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose) on Meta-Wiki
2. Fill in the form:
   - **Application name**: Something like `Montage local dev (<your username>)`
   - **Callback URL**: `http://localhost:5001/complete_login`
   - **Applicable grants**: "Basic rights" is sufficient
3. Save the **consumer token** and **consumer secret** you receive
4. Copy `config.default.yaml` to `config.dev.yaml` and set:
   ```yaml
   debug: False
   oauth_consumer_token: "<your consumer token>"
   oauth_secret_token: "<your consumer secret>"
   ```

See the [MediaWiki OAuth developer guide](https://www.mediawiki.org/wiki/OAuth/For_Developers) for more details on the OAuth flow. For Toolforge-specific OAuth setup, see the [Toolforge documentation](https://wikitech.wikimedia.org/wiki/Help:Toolforge).

### 5. Run the Frontend in Development Mode
```bash
npm run dev
```

This will start the Vite development server with hot module replacement.

Other frontend development commands:
* `npm run build`: Build for production
* `npm run lint`: Lint and auto-fix
* `npm run format`: Format with Prettier
* `npm run lint:check`: Lint without auto-fix (same as CI)
* `npm run format:check`: Check formatting without writing (same as CI)

### 6. Use the Makefile to start the backend
* Open a new terminal tab and change directory to root of repo
* Copy and edit `config.dev.yaml` based on `config.default.yaml`
* (Optional) In `config.dev.yaml` there is a line for `dev_local_cookie_value`. To get it,
log in to the local app in your browser, and then copy the value from the
`clastic_cookie` in the apps' cookies. This is your login cookie.
* (Optional) Add your username as the `superuser` in the config. (This will allow you to
add `su_to=<any user>` to the backend, if you want to test submitting as another
juror.)
* Add your username to the list of maintainers in [rdb.py line 113](https://github.com/hatnote/montage/blob/master/montage/rdb.py#L113).
This will give your user top-level permissions in the full app, so you can view
some logs (audit logs, active users), add/remove organizers, and get a
coordinator view into all campaigns.
* Start the montage backend
```bash
make start
```
This will build the docker image for the montage backend and start the container. Apart from `make start`, these are other commands:
* `make start-detached` : Start the backend container in detached mode
* `make stop` : Stop the backend container
* `make logs` : Stream the backend container logs in real-time.
* `make restart` : Restart the backend container

### 7. Access the Application
* With development server: Open http://localhost:5173 in your browser (frontend)
* With backend serving frontend: Open http://localhost:5001 in your browser

The application server runs on localhost port 5001, visit [http://localhost:5001/meta](http://localhost:5001/meta) to see a list
of valid URL patterns and other details.

Almost all endpoints from backend (except for OAuth and `/static/`) return JSON as long as the proper Accept header is set (done by most libraries) or `format=json` is passed in the query string.

---

## Pre-commit Hooks

Install [pre-commit](https://pre-commit.com/) to catch lint and formatting issues before they reach CI:

```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically on `git commit`. To run on all files manually:

```bash
pre-commit run --all-files
```

The hooks mirror what CI checks:
* **Prettier**: auto-formats staged frontend files
* **ESLint**: lints staged frontend files
* **Ruff**: checks Python syntax errors and undefined names

---

## CI

Pull requests are checked by GitHub Actions (`.github/workflows/`):

* **Backend**: Docker build, pytest, Python import verification
* **Frontend**: Prettier formatting, ESLint, Vite build

Changes are only checked if they touch the relevant paths (e.g., frontend-only changes skip backend tests).

To run the same checks locally:

```bash
# Backend tests
docker build -t montage-ci -f dockerfile .
docker run --rm -v $(pwd):/app -e PYTHONPATH=/app montage-ci \
  python -m pytest montage/tests/test_web_basic.py -v --tb=short

# Frontend checks
cd frontend
npx prettier --check src/
npx eslint src/ --ext .vue,.js,.jsx,.cjs,.mjs
npm run build
```

## Project structure
```bash
├── DEV.md
├── Dockerfile
├── LICENSE
├── MANIFEST.in
├── Makefile
├── PROJECT_LOG.md
├── config
│   ├── beta-uwsgi.ini
│   ├── dev-uwsgi.ini
│   └── prod-uwsgi.ini
├── config.default.yaml
├── deployment.md
├── design.md
├── docker-compose.yml
├── frontend
│   ├── index.html
│   ├── jsconfig.json
│   ├── package-lock.json
│   ├── package.json
│   ├── .env.default
│   ├── public
│   ├── src
│   └── vite.config.js
├── montage
│   ├── __init__.py
│   ├── __main__.py
│   ├── __pycache__
│   ├── admin_endpoints.py
│   ├── app.py
│   ├── check_rdb.py
│   ├── clastic_sentry.py
│   ├── docs
│   ├── imgutils.py
│   ├── juror_endpoints.py
│   ├── labs.py
│   ├── loaders.py
│   ├── log.py
│   ├── meta_endpoints.py
│   ├── mw
│   ├── public_endpoints.py
│   ├── rdb.py
│   ├── rendered_admin.py
│   ├── server.py
│   ├── simple_serdes.py
│   ├── static
│   ├── templates
│   ├── tests
│   └── utils.py
├── report.html
├── requirements-dev.txt
├── requirements.in
├── requirements.txt
├── setup.py
├── tools
│   ├── _admin.py
│   ├── admin.py
│   ├── check_schema.py
│   ├── create_schema.py
│   ├── drop_schema.py
│   └── trim_csv.py
└── tox.ini
```
These provides a detailed explanation of the main components in the **Montage Project**.

#### Directory: `montage`
##### **Core Files**
- **`app.py`**: Initializes the application and defines middleware, routes, or app-wide configurations.
- **`server.py`**: Starts the server, setting up the backend to listen on a specific port.
- **`__main__.py`**: Entry point when running the backend module.

##### **API Endpoints**
- **`admin_endpoints.py`**: Handles admin-specific routes (e.g., user management, settings).
- **`juror_endpoints.py`**: Contains juror-related APIs (e.g., task assignments, voting).
- **`meta_endpoints.py`**: General application metadata or system information.
- **`public_endpoints.py`**: APIs accessible to public or unauthenticated users.

##### **Utilities**
- **`imgutils.py`**: Handles image processing and manipulation.
- **`simple_serdes.py`**: Serializes and deserializes objects to JSON or other formats.
- **`log.py`**: Configures application logging.

##### **Database**
- **`rdb.py`**: Manages database interactions (queries, migrations, etc.).
- **`check_rdb.py`**: Verifies database schema integrity.

##### **Static and Templates**
- **`static/`**: Holds CSS, JavaScript, and other assets.
- **`templates/`**: Contains Jinja2 templates for dynamic HTML rendering.

##### **Testing**
- **`tests/`**: Basic tests for backend components.


#### Directory: `frontend`

##### **Core Files**
- **`src/`**: Source code, including components, routes, and utilities.
- **`public/`**: Static assets, such as images and global styles.
- **`vite.config.js`**: Configuration for the Vite build tool.
- **`.env.default`**: Template for environment configuration.


#### Directory: `tools`

##### **Key Scripts**
- **`create_schema.py`**: Creates database tables.
- **`drop_schema.py`**: Drops all database tables.
- **`check_schema.py`**: Verifies schema correctness.
- **`trim_csv.py`**: Utility for cleaning CSV files


#### Docker Files
- **`Dockerfile`**: Builds the backend container.
- **`docker-compose.yml`**: Orchestrates service for backend.