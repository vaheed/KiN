.PHONY: test test-integration validate compose-config lint format-check

test:
	PYTHONPATH=core pytest -q core/tests -m 'not integration'

test-integration:
	KiN_RUN_INTEGRATION=1 PYTHONPATH=core pytest -q core/tests -m integration

validate:
	python -m compileall -q core/app core/tests
	python -c 'import json; json.load(open("infra/bifrost/config.json")); print("JSON OK")'
	python -c 'import yaml; yaml.safe_load(open("compose.yml")); print("YAML OK")'
	python -c 'import re; from pathlib import Path; t=Path("ARCHITECTURE.md").read_text(); blocks=re.findall(r"```mermaid\n.*?\n```", t, re.S); assert len(blocks)==t.count("```mermaid"); print("Mermaid blocks:", len(blocks))'

compose-config:
	docker compose -f compose.yml config

format-check:
	python -m compileall -q core/app core/tests

lint:
	python -m compileall -q core/app core/tests
