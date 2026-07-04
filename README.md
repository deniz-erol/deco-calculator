# Deco Calculator

An academic-prototype web tool that reproduces **US Navy Diving Manual (Rev 7) decompression
tables** for air, nitrox (via Equivalent Air Depth), and heliox dives, including repetitive
(consecutive) dive chaining and per-user saved profiles.

> **SAFETY / SCOPE DISCLAIMER** — This is an academic prototype built for a thesis presentation.
> It is **NOT** a certified dive-planning tool and must never be used for operational dive
> planning. Decompression errors cause injury or death.

It is a **faithful table-lookup calculator** — no decompression algorithm, no gas-switching
engine. See [`docs/spec.md`](docs/spec.md) and
[`docs/research/usn-rev7-reference.md`](docs/research/usn-rev7-reference.md) for the full design
and table references, and [`engine/tables/SOURCES.md`](engine/tables/SOURCES.md) for per-table
provenance and verification status. The tables are transcribed from the official US Navy Rev 7
tables (air, heliox) or formula-derived (nitrox EAD), but are **not yet verified cell-by-cell
against a physical manual** — every table is still marked `verified: false`.

## Run locally

Use the project virtual environment (`.venv`):

```bash
.venv/Scripts/streamlit run app/Home.py
```

Then open http://localhost:8501.

To (re)create the environment from scratch:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

## Deploy to Streamlit Community Cloud

The app is a public-safe, read-only calculator (no secrets, no writable server state required).
To deploy:

1. Push this repository to GitHub (branch `main`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the repo, branch **`main`**, and main file path **`app/Home.py`**.
4. Python version: **3.12**. Dependencies come from [`requirements.txt`](requirements.txt).
5. Click **Deploy**.

> **SAFETY** — the deployed app carries the same disclaimer: it is an unverified academic
> prototype and must **never** be used for real dive planning.

## Run the tests

```bash
.venv/Scripts/python -m pytest tests -q
```

## Architecture

```
UI (Streamlit)  ->  App (profile store)  ->  Engine (pure table lookup)  ->  Data (versioned JSON)
```

The `engine/` package has zero dependency on `app/` or Streamlit — it is independently testable,
which is the whole credibility story for this tool. See `docs/spec.md` §3–§5 for details.
