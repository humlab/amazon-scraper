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

mypy-strict: export PYTHONPATH=.
mypy-strict:
	@poetry run mypy $(MYPY_ARGS) --strict $(SOURCE_FOLDERS) || true
.PHONY: mypy-strict

typing: lint mypy
.PHONY: typing

typing-strict: lint mypy-strict
.PHONY: typing-strict

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

test-no-slow:
	@poetry run pytest -m "not slow" --durations=0 tests/
.PHONY: test-no-slow

test-no-slow-no-web:
	@poetry run pytest -m "not slow and not web" --durations=0 tests/
.PHONY: test-no-slow-no-web

test-coverage:
	@poetry run pytest --durations=0 --cov=$(PACKAGE_FOLDER) --cov-report=xml --cov-report=html --cov-branch tests/
.PHONY: test-coverage

test-web:
	@poetry run pytest -m "web" tests/
.PHONY: test-web

test-retest:
	@poetry run pytest --durations=0 --last-failed tests
.PHONY: test-retest

TIMESTAMP_IN_ISO_FORMAT=$(shell date -u +"%Y%m%dT%H%M%SZ")

profile-with-pyinstrument: export PYTHONPATH=.
profile-with-pyinstrument:
	@echo "Profiling scrape workflow..."
	@mkdir -p tests/output
	@poetry run pyinstrument --color --show-all \
		-o tests/output/$(TIMESTAMP_IN_ISO_FORMAT)_profile_workflow.html \
			tests/profile_workflow.py
.PHONY: profile-with-pyinstrument

profile-with-cprofile: export PYTHONPATH=.
profile-with-cprofile:
	@echo "Profiling scrape workflow..."
	@mkdir -p tests/output
	@poetry run python -m cProfile tests/profile_workflow.py &> tests/output/$(TIMESTAMP_IN_ISO_FORMAT)_profile_workflow.txt
.PHONY: profile-with-cprofile

profile-with-snakeviz: export PYTHONPATH=.
profile-with-snakeviz:
	@echo "Profiling scrape workflow..."
	@mkdir -p tests/output
	@poetry run python -m cProfile -o tests/output/$(TIMESTAMP_IN_ISO_FORMAT)_profile_workflow.prof tests/profile_workflow.py
	@poetry run snakeviz tests/output/$(TIMESTAMP_IN_ISO_FORMAT)_profile_workflow.prof

md5sums-windows:
	@cd output && find -type f ! -name "output.md5" -exec md5sum -b {} + > output.md5
	@sed 's/\//\\/g; s/\.\\//g' output/output.md5 > output/output.md5.tmp
	@mv output/output.md5.tmp output/output.md5
.PHONY: md5sums

sha256sums-windows:
	@cd output && find -type f ! -name "output.sha256" -exec sha256sum -b {} + > output.sha256
	@sed 's/\//\\/g; s/\.\\//g' output/output.sha256 > output/output.sha256.tmp
	@mv output/output.sha256.tmp output/output.sha256
.PHONY: sha256sums

help:
	@echo "black:				Run black formatter"
	@echo "isort:				Run isort formatter"
	@echo "tidy:				Run black and isort formatters"
	@echo "pylint:				Run pylint"
	@echo "lint:				Run black, isort and pylint"
	@echo "notes:				Run pylint to show notes"
	@echo "mypy:				Run mypy"
	@echo "typing:				Run lint and mypy"
	@echo "clean:				Remove all temporary files"
	@echo "test:				Run all tests"
	@echo "test-no-web:			Run all tests except the ones that require internet connection"
	@echo "test-no-slow:			Run all tests except the slow ones"
	@echo "test-no-slow-no-web:		Run all tests except the slow ones and the ones that require internet connection"
	@echo "test-coverage:			Run all tests and generate coverage report"
	@echo "test-web:			Run only tests that require internet connection"
	@echo "test-retest:			Run only the tests that failed in the last run"
	@echo "profile-with-pyinstrument:	Profile scrape workflow with pyinstrument"
	@echo "profile-with-cprofile:		Profile scrape workflow with cProfile"
	@echo "md5sums-windows:		Generate md5sums of output files for Windows"
	@echo "sha256sums-windows:		Generate sha256sums of output files for Windows"
.PHONY: help