"""DeerFlow-compatible Gateway entry (harness venv only, port 8011).

Run via ``scripts/run-harness-gateway.ps1``. Channel Worker and LangGraph
``/api/*`` runs live here; main RAG API stays on 8010 (``.venv``).
"""

from app.gateway.app import create_app

app = create_app()
