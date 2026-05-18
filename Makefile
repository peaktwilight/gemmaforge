# GemmaForge — convenience targets.
# Run `make help` for a list of available targets.

PYTHON ?= python3
VENV   ?= .venv

.PHONY: help install dataset extract probe serve test demo-record hf-deploy clean

help: ## show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-14s\033[0m %s\n", $$1, $$2}'

install: ## create .venv and install requirements.txt
	$(PYTHON) -m venv $(VENV) && . $(VENV)/bin/activate && pip install -r requirements.txt

dataset: ## build the pairs.jsonl training dataset
	$(PYTHON) scripts/build_dataset.py

extract: ## extract hidden-state activations for the probe
	$(PYTHON) -m src.extract_activations

probe: ## train the linear probe on data/pairs.jsonl
	$(PYTHON) -m src.train_probe --pairs data/pairs.jsonl

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
