.PHONY: help test install edx-sources clean-test test-all

.DEFAULT_GOAL := help

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

test-all: ## run tests against every supported Open edX release
	$(MAKE) test RELEASE=redwood
	$(MAKE) test RELEASE=verawood

## Tests against one Open edX release

# The Open edX release to test against. Each one has its own constraints file,
# edx-platform tag and Python version, below.
RELEASE ?= verawood

ifeq ($(RELEASE),redwood)
PYTHON ?= python3.11
EDX_PLATFORM_REF ?= open-release/redwood.2
else ifeq ($(RELEASE),verawood)
PYTHON ?= python3.12
EDX_PLATFORM_REF ?= release/verawood.2
else
$(error RELEASE must be redwood or verawood, not $(RELEASE))
endif

VENV ?= .venv-$(RELEASE)
BIN := $(VENV)/bin
CONSTRAINTS := tests/constraints-$(RELEASE).txt
EDX_SOURCES ?= .edx-sources/$(RELEASE)
# Studio installs this and the plugin imports it, but setup.py does not list it.
FROM_EDX_PLATFORM := edx-opaque-keys

test: install edx-sources ## run the tests against RELEASE (redwood or verawood, default verawood)
	EDX_PLATFORM_ROOT=$(EDX_SOURCES)/edx-platform $(BIN)/pytest

install: $(BIN)/pytest

$(BIN)/pytest: Makefile $(CONSTRAINTS) setup.py requirements/base.in
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --quiet --upgrade pip
	$(BIN)/pip install --quiet -c $(CONSTRAINTS) pytest pytest-cov pytest-django $(FROM_EDX_PLATFORM) -e .
	touch $@

# The edx-platform source tests/test_edx_contract.py reads. Only the deepest
# directories that hold a stand-in in mock_apps are checked out. Cone-mode sparse
# checkout takes a named directory with everything below it, and also the files
# sitting directly in each of its parents. So naming lms because of
# mock_apps/lms/__init__.py would check out all of lms. Naming lms/djangoapps/instructor
# already brings lms/__init__.py.
EDX_STUB_DIRS := $(shell cd mock_apps && find cms common lms openedx xmodule -name '*.py' 2>/dev/null \
	| xargs -n1 dirname | sort -u \
	| awk '{ d[NR] = $$0 } END { for (i = 1; i <= NR; i++) { leaf = 1; for (j = 1; j <= NR; j++) if (index(d[j], d[i] "/") == 1) leaf = 0; if (leaf) print d[i] } }')

edx-sources: $(EDX_SOURCES)/edx-platform/.sparse-$(RELEASE)

$(EDX_SOURCES)/edx-platform/.sparse-$(RELEASE): Makefile $(shell find mock_apps -name '*.py')
	rm -rf $(EDX_SOURCES)/edx-platform
	git clone --quiet --depth 1 --branch $(EDX_PLATFORM_REF) --filter=blob:none --sparse \
		https://github.com/openedx/edx-platform.git $(EDX_SOURCES)/edx-platform
	git -C $(EDX_SOURCES)/edx-platform sparse-checkout set $(EDX_STUB_DIRS)
	touch $@

clean-test: ## remove the test virtualenvs and edx-platform source
	rm -rf .venv-redwood .venv-verawood .edx-sources
