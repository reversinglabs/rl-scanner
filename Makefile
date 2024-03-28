# the envfile has the 2 required environment variables:
# RLSECURE_SITE_KEY=
# RLSECURE_ENCODED_LICENSE=

ifdef DOCKER_TAG
    BUILD_VERSION	:= $(DOCKER_TAG)
else
    BUILD_VERSION=latest
endif

VOLUMES 		:= -v ./output:/output -v ./input:/input
USER_GROUP		:= $(shell id -u):$(shell id -u )

COMMON_DOCKER	:= -i --rm -u $(USER_GROUP) --env-file=$(HOME)/.envfile_rl-scanner.docker

# IMAGE_NAME		:= rlsecure/scanner:latest
IMAGE_BASE		:= reversinglabs/rl-scanner
IMAGE_NAME		:= $(IMAGE_BASE):$(BUILD_VERSION)

ARTIFACT_OK		:=	vim
ARTIFACT_ERR	:=	eicarcom2.zip

LINE_LENGTH = 120

IMAGE ?= reversinglabs/rl-scanner
TAG   ?= latest

.PHONY: build clean

all: clean prep format build testFail test_ok test_err clean

prep:
	wget 'https://www.eicar.org/download/eicar-com-2-2/?wpdmdl=8848&refresh=65d33af627b351708342006' --output-document 'eicarcom2.zip'

# build a new docker image from the Dockerfile generated
build:
	mkdir -p tmp
	docker build -t $(IMAGE_NAME) -f Dockerfile .
	docker image ls $(IMAGE_NAME) | tee ./tmp/image_ls.txt
	docker image inspect $(IMAGE_NAME) --format '{{ .Config.Labels }}'
	docker image inspect $(IMAGE_NAME) --format '{{ .RepoTags }}'

testFail:
	# we know that specifying no arguments should print usage() and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) # will fail but we will ignore that
	# we know that specifying no arguments to rl-scan should print usage() and fail
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) rl-scan # will fail but we will ignore that

test_ok:
	rm -rf output input
	mkdir -m 777 -p input output
	cp /bin/$(ARTIFACT_OK) ./input/$(ARTIFACT_OK)
	docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) rl-scan --package-path=/input/$(ARTIFACT_OK) --report-path=/output
	ls -laR input output >./tmp/list_in_out_ok.txt
	cat output/report.rl.json | jq -r . >tmp/test_ok.json

test_err:
	rm -rf output input
	mkdir -m 777 -p input output
	curl -o $(ARTIFACT_ERR) -sS https://secure.eicar.org/$(ARTIFACT_ERR)
	cp $(ARTIFACT_ERR) ./input/$(ARTIFACT_ERR)
	# as we are now scanning a item that makes the scan fail (non zero exit code) we have to ignore the error in the makefile
	-docker run $(COMMON_DOCKER) $(VOLUMES) $(IMAGE_NAME) rl-scan --package-path=/input/$(ARTIFACT_ERR) --report-path=/output
	ls -laR input output >./tmp/list_in_out_err.txt
	cat output/report.rl.json | jq -r . >tmp/test_err.json

clean:
	docker image prune -f
	-docker image rm $(IMAGE_NAME)
	rm -f eicarcom2.zip
	rm -rf .mypy_cache */.mypy_cache

format:
	black --line-length $(LINE_LENGTH) scripts/*

