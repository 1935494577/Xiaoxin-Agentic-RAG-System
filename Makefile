.PHONY: install install-official install-torch-gpu install-torch-gpu-cn infra-up infra-down run-api run-dev run-frontend stop-dev test verify-env eval e2e demo build-rag up down

PY ?= python
PIP_MIRROR := https://pypi.tuna.tsinghua.edu.cn/simple
PIP_TRUSTED := pypi.tuna.tsinghua.edu.cn
PIP_INSTALL := $(PY) -m pip install -i $(PIP_MIRROR) --trusted-host $(PIP_TRUSTED)
SRC := enterprise_rag/src

# 中国地区默认走清华 PyPI；需要官方 PyPI 时用 install-official
install:
	$(PIP_INSTALL) -r requirements.txt

install-official:
	$(PY) -m pip install -r requirements.txt

# RTX 3060 等 NVIDIA GPU：安装 CUDA 版 PyTorch（6GB 建议 cu124 或按驱动选版本）
install-torch-gpu:
	$(PY) -m pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 国内：PyPI 走镜像 + PyTorch CUDA 轮子走官方 index（依赖解析更稳）
install-torch-gpu-cn:
	$(PY) -m pip install --upgrade torch torchvision torchaudio -i $(PIP_MIRROR) --trusted-host $(PIP_TRUSTED) --extra-index-url https://download.pytorch.org/whl/cu124

infra-up:
	docker compose -f docker-compose.yml --profile legacy up -d

infra-down:
	docker compose -f docker-compose.yml down --remove-orphans

run-api:
	cd $(SRC) && $(PY) -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8010

run-dev:
	bash scripts/run-dev.sh

stop-dev:
	bash scripts/stop-dev.sh

run-frontend:
	$(PY) -m streamlit run frontend/streamlit_app.py --server.port 8501

test:
	$(PY) -m pytest tests/

# Tests + import api.main (run from repo root; use .venv Python if you use scripts/bootstrap_venv.ps1)
verify-env:
	$(PY) -m pytest tests/ -q
	cd $(SRC) && $(PY) -c "from api.main import app; print('api.main OK:', app.title)"

eval:
	cd $(SRC) && $(PY) -m evaluation.ragas_scorer

e2e:
	$(PY) scripts/run_closed_loop.py

build-rag:
	docker compose -f docker-compose.yml --profile app build rag-api

up: infra-up

down: infra-down

demo:
	@echo "plan1 (no Docker): make install && python scripts/run_closed_loop.py"
	@echo "Dev (all):  Windows: scripts/run-dev.ps1   macOS: ./scripts/run-dev.sh"
	@echo "API only:   make run-api   Frontend: make run-frontend"
	@echo "Deploy/security: docs/deploy_security.md"
	@echo "Windows venv: powershell -File scripts/bootstrap_venv.ps1 && powershell -File scripts/verify_env.ps1"
	@echo "Legacy stack: make infra-up  (docker compose --profile legacy)"
	@echo "Eval: copy enterprise_rag/data/eval/golden.example.jsonl to golden.jsonl then: make eval"
