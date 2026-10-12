PYTHON ?= python3
.PHONY: test validate eval dev
test:
	$(PYTHON) -m unittest discover -s tests -v
validate:
	$(PYTHON) run.py --validate
eval:
	$(PYTHON) run.py --split all
dev:
	$(PYTHON) run.py --split dev
online-demo:
	$(PYTHON) online_eval.py --scenario drift
