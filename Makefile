.PHONY: test coverage quality ci

test:
	python -m pytest -q

coverage:
	python -m pytest --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml

quality:
	python -m src.data_quality

ci: test coverage quality
