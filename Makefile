SHELL := /bin/bash
SOURCE_FOLDERS=amazon_scraper tests
PACKAGE_FOLDER=amazon_scraper
BLACK_ARGS=--line-length 120 --target-version py311 --skip-string-normalization -q
MYPY_ARGS=--show-column-numbers --no-error-summary --python-version 3.11
ISORT_ARGS=--profile black --float-to-top --line-length 120 --py 311

black:
	@poetry run black $(BLACK_ARGS) $(SOURCE_FOLDERS)
.PHONY: black

isort:
	@poetry run isort $(ISORT_ARGS) $(SOURCE_FOLDERS)
.PHONY: isort

tidy: isort black
.PHONY: tidy

pylint:
	@poetry run pylint $(SOURCE_FOLDERS)
.PHONY: pylint

lint: tidy pylint
.PHONY: lint

notes:
	@poetry run pylint --notes=FIXME,XXX,TODO --disable=all --enable=W0511 -f colorized $(SOURCE_FOLDERS)
.PHONY: notes

mypy: export PYTHONPATH=.
mypy:
	@poetry run mypy $(MYPY_ARGS) $(SOURCE_FOLDERS) || true
.PHONY: mypy

typing: lint mypy
.PHONY: typing

clean:
	@rm -rf .coverage coverage.xml htmlcov
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@rm -rf tests/output
.PHONY: clean

test: export PYTHONPATH=.
test:
	@poetry run pytest --durations=0 tests/
.PHONY: test

test-no-web:
	@poetry run pytest -m "not web" --durations=0 tests/
.PHONY: test-no-web

test-coverage:
	@poetry run pytest --durations=0 --cov=$(PACKAGE_FOLDER) --cov-report=xml --cov-report=html --cov-branch tests/
.PHONY: test-coverage

test-web:
	@poetry run pytest -m "web" tests/
.PHONY: test-web

test-retest:
	@poetry run pytest --durations=0 --last-failed tests
.PHONY: test-retest

help:
	@echo "black:			Run black formatter"
	@echo "isort:			Run isort formatter"
	@echo "tidy:			Run black and isort formatters"
	@echo "pylint:			Run pylint"
	@echo "lint:			Run black, isort and pylint"
	@echo "notes:			Run pylint to show notes"
	@echo "mypy:			Run mypy"
	@echo "typing:			Run lint and mypy"
	@echo "clean:			Remove all temporary files"
	@echo "test:			Run all tests"
	@echo "test-no-web:		Run all tests except the ones that require internet connection"
	@echo "test-coverage:		Run all tests and generate coverage report"
	@echo "test-web:		Run only tests that require internet connection"
	@echo "test-retest:		Run only the tests that failed in the last run"
.PHONY: help