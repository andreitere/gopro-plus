.PHONY: sync test docker-build

sync:            ## uv sync: create/refresh the virtualenv
	uv sync

test:            ## run the test suite
	uv run pytest

docker-build:    ## build the docker image
	docker build -t goproplus:latest .
