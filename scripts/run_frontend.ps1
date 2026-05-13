$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m streamlit run frontend/streamlit_app.py --server.port 8501
