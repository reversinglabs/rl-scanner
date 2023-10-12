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

COMMON_DOCKER	:= -i --rm -u $(USER_GROUP) --env-file=.envfile

# IMAGE_NAME		:= rlsecure/scanner:latest
IMAGE_BASE		:= reversinglabs/rl-scanner
IMAGE_NAME		:= $(IMAGE_BASE):$(BUILD_VERSION)

ARTIFACT_OK		:=	vim
ARTIFACT_ERR	:=	eicarcom2.zip

all: clean format build testFail test_ok test_err

format:
	./reformat-code.sh

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
	rm -rf input output tmp
	rm -f eicarcom2.zip
	rm -rf .mypy_cache */.mypy_cache

push:
	docker push $(IMAGE_NAME)
	docker pushrm $(IMAGE_NAME)

tag:
	echo "not yet functional"
	exit 1
	git tag -a v1.0.0 -m "version v1.0.0"
	git push --tags
