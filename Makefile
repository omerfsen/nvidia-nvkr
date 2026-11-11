# omerfsen.nvkr. Run `make help` for targets.
SHELL := /bin/bash
VENV := .venv
BIN := $(VENV)/bin
PYTHON ?= python3

.PHONY: help dev lint docs components quickstart release handoff build

help:
	@echo "  make dev           venv + dependencies + this repo linked as omerfsen.nvkr"
	@echo "  make lint          ansible-lint (production profile) and playbook syntax"
	@echo "  make docs          regenerate docs/variables.md from the argument specs"
	@echo "  make components    regenerate docs/components.md from this host's build"
	@echo "  make quickstart    smoke test: NVKR's hello example built, published and checked"
	@echo "  make release       NVKE outputs: nvkectl, seed images and the node image"
	@echo "  make handoff       hand the NVKR outputs to omerfsen.nvke"
	@echo "  make build         build the collection tarball for Galaxy"

$(BIN)/ansible-playbook:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -q -r requirements.txt

dev: $(BIN)/ansible-playbook
	$(BIN)/ansible-galaxy collection install -r requirements.yml -p .collections
	mkdir -p .collections/ansible_collections/omerfsen
	ln -sfn ../../.. .collections/ansible_collections/omerfsen/nvkr

lint: dev
	$(BIN)/ansible-lint --profile production
	$(BIN)/ansible-playbook --syntax-check playbooks/*.yml

docs: dev
	$(BIN)/python tools/gen-variables-doc.py

components: dev
	$(BIN)/python tools/gen-components-doc.py

quickstart: dev
	$(BIN)/ansible-playbook playbooks/quickstart.yml

release: dev
	$(BIN)/ansible-playbook playbooks/nvke_release.yml

handoff: dev
	$(BIN)/ansible-playbook playbooks/handoff.yml

build: dev
	$(BIN)/ansible-galaxy collection build --force
