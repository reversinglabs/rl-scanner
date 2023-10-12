
IMAGE ?= reversinglabs/rl-scanner
TAG   ?= latest

.PHONY: build clean push

build:
	docker build -t $(IMAGE):$(TAG) .

push: build
	docker push $(IMAGE):$(TAG)
	
clean:
	-docker rmi $(IMAGE):$(TAG)
