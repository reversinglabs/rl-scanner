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
LINE_LENGTH = 120
PL_LINTERS = "eradicate,mccabe,pycodestyle,pyflakes,pylint"
PL_IGNORE = C0114,C0115,C0116
SCRIPTS = scripts/


.PHONY: build-without-cache build-with-cache push clean format pycheck test test.%

all: clean prep build test

prep: format pylama mypy

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
	rm -rf ./tests/repro/store/
	rm -rf ./tests/repro/report_base/
	rm -rf ./tests/repro/report_repro_fail/
	rm -rf ./tests/repro/report_repro_ok/

format:
	black \
		--line-length $(LINE_LENGTH) \
		$(SCRIPTS)/*

pylama:
	pylama \
		--max-line-length $(LINE_LENGTH) \
		--linters $(PL_LINTERS) \
		--ignore $(PL_IGNORE) \
		$(SCRIPTS)

mypy:
	mypy \
		--strict \
		--no-incremental \
		$(SCRIPTS)


all-tests :=  $(addprefix test., $(notdir $(wildcard tests/*)))

test.%: tests/%/run.sh
	cd $(dir $<) && ./run.sh "$(IMAGE_NAME)"

test: $(all-tests)
