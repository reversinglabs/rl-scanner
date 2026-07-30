# Makefile: keep tabs
SHELL := /bin/bash -l
export SHELL

VENV := ./vtmp/
export VENV

# rockylibux:10-minimal uses 3.12
MIN_PYTHON_VERSION := $(shell basename $$( ls /usr/bin/python3.12 | awk '{print $0; exit}' ) )
export MIN_PYTHON_VERSION

COMMON_VENV := rm -rf $(VENV); \
	$(MIN_PYTHON_VERSION) -m venv $(VENV); \
	source ./$(VENV)/bin/activate;

PIP_INSTALL := pip3 -q \
	--require-virtualenv \
	--disable-pip-version-check \
	--no-color install --no-cache-dir

MYPY_INSTALL := # empty for now

DO_MYPY := 	$(COMMON_VENV) $(PIP_INSTALL) mypy $(MYPY_INSTALL); mypy --strict --no-incremental

# Makefile expects 2 required environment variables for
#   build-with-cache and test targets:
# RLSECURE_ENCODED_LICENSE=
# RLSECURE_SITE_KEY=

ifeq ($(strip $(RLSECURE_ENCODED_LICENSE)),)
    $(error  mandatory RLSECURE_ENCODED_LICENSE not set!)
endif

ifeq ($(strip $(RLSECURE_SITE_KEY)),)
    $(error  mandatory RLSECURE_SITE_KEY not set!)
endif

IMAGE_NAME ?= reversinglabs/rl-scanner:test

SCRIPTS = scripts/

RL_SCAN = scripts/rl-scan
RL_SCAN_URL = scripts/rl-scan-url
RL_SCAN_PURL = scripts/rl-scan-purl
RL_SCAN_DOCKER = scripts/rl-scan-docker
RL_PRUNE = scripts/rl-prune
RL_ENTRYPOINT = scripts/entrypoint

RL_COMMANDS := $(RL_SCAN) $(RL_SCAN_URL) $(RL_SCAN_PURL) $(RL_SCAN_DOCKER) $(RL_PRUNE) $(RL_ENTRYPOINT)

.PHONY: build-without-cache build-with-cache push clean format pycheck test test.%

all: clean prep build test

prep: format check mypy

build: build-with-cache

build-without-cache:
	docker buildx build . -f Dockerfile.no_cache \
	--no-cache \
	-t $(IMAGE_NAME)

#	--build-arg CACHE_PATH=/tmp/rl-secure.cache
build-with-cache:
	docker buildx build . -f Dockerfile.cache \
	--no-cache \
	--secret id=rlsecure_license,env=RLSECURE_ENCODED_LICENSE \
	--secret id=rlsecure_sitekey,env=RLSECURE_SITE_KEY \
	-t $(IMAGE_NAME)

clean:
	-docker rmi $(IMAGE_NAME)
	rm -rf ./tests/*/report/
	rm -rf ./tests/*repro/store/
	rm -rf ./tests/*repro/report_base/
	rm -rf ./tests/*repro/report_repro_fail/
	rm -rf ./tests/*repro/report_repro_ok/

format:
	ruff format $(SCRIPTS) $(RL_COMMANDS)

check:
	ruff check --fix $(SCRIPTS) $(RL_COMMANDS)

mypy: mypy_a mypy_prune \
	mypy_scan \
	mypy_scan_url \
	mypy_scan_purl \
	mypy_scan_docker \
	mypy_entry

mypy_a:
	$(DO_MYPY) $(SCRIPTS)

mypy_prune:
	$(DO_MYPY) $(SCRIPTS) $(RL_PRUNE)

mypy_scan:
	$(DO_MYPY) $(SCRIPTS) $(RL_SCAN)

mypy_scan_url:
	$(DO_MYPY) $(SCRIPTS) $(RL_SCAN_URL)

mypy_scan_purl:
	$(DO_MYPY) $(SCRIPTS) $(RL_SCAN_PURL)

mypy_scan_docker:
	$(DO_MYPY) $(SCRIPTS) $(RL_SCAN_DOCKER)

mypy_entry:
	$(DO_MYPY) $(SCRIPTS) $(RL_ENTRYPOINT)

all-tests :=  $(addprefix test., $(notdir $(wildcard tests/*)))

test.%: tests/%/run.sh
	cd $(dir $<) && ./run.sh "$(IMAGE_NAME)"

test: $(all-tests)
