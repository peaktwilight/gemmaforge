# GemmaForge — convenience targets.
# Run `make help` for a list of available targets.

PYTHON ?= python3
VENV   ?= .venv
REPO   ?= .

.PHONY: help install dataset extract probe spanmax-probe scan repo-benchmark repo-scan serve test demo-record hf-deploy clean

help: ## show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

install: ## create .venv and install requirements.txt
	$(PYTHON) -m venv $(VENV) && . $(VENV)/bin/activate && pip install -r requirements.txt

dataset: ## build the canonical SVEN before/after token dataset
	$(PYTHON) scripts/build_dataset.py

extract: ## extract sample-level hidden-state activations for the baseline probe
	$(PYTHON) -m src.extract_activations

probe: ## train the sample-level baseline probe on data/pairs.jsonl
	$(PYTHON) -m src.train_probe --pairs data/pairs.jsonl

spanmax-probe: ## train the token-level span-max probe from data/token_activations
	$(PYTHON) -m src.train_probe_spanmax

scan: ## scan a repo path: make scan REPO=./examples/vuln-express-app
	$(PYTHON) -m src.scan $(REPO)

repo-benchmark: ## build the held-out repo benchmark fixtures
	$(PYTHON) scripts/build_repo_benchmark.py --input data/dataset_sven_heldout.jsonl --out-root data/repo_benchmark_heldout --max-repos 9999

repo-scan: ## run the repo-level benchmark scan over data/repo_benchmark_heldout
	$(PYTHON) scripts/run_repo_scan_benchmark.py --benchmark-root data/repo_benchmark_heldout --resume

serve: ## launch the streaming probe inference server
	$(PYTHON) -m src.stream_with_probe --serve

test: ## run the pytest suite
	$(PYTHON) -m pytest tests/ -v

demo-record: ## record the demo GIFs / screencasts
	$(PYTHON) scripts/record_demo.py

hf-deploy: ## deploy the Hugging Face Space
	bash scripts/deploy_hf.sh

clean: ## remove venv, generated activations, and python/pytest caches
	rm -rf $(VENV) data/activations/ data/token_activations/ __pycache__ .pytest_cache
