# Shortcuts around docker compose so nobody has to remember the underlying
# `docker compose run` invocation. All of these run inside the toolchain
# container defined in Dockerfile/docker-compose.yml, against the repo
# bind-mounted at /workspace -- see README.md for what each arg means.
#
#   make build                                       # build the toolchain image (once, or after Dockerfile changes)
#   make generate PROFILE=acl1 COUNT=1000             # -> data/acl1_1000/{ruleset.txt,trace.txt}
#   make classify-cpp NAME=acl1_1000                  # build + run the C++ LinearSearch classifier
#   make classify-py NAME=acl1_1000                   # run the Python pipeline (numpy engine)
#   make compare NAME=acl1_1000                       # classify with both + diff their per-packet results
#   make test NAME=acl1_1000                          # generate + classify with both, one shot
#   make shell                                        # drop into the container

RUN := docker compose run --rm dev

PROFILE ?= acl1
COUNT ?= 1000
NAME ?= $(PROFILE)_$(COUNT)
ENGINE ?= numpy
CLASSIFIER ?= linear

.PHONY: build generate classify-cpp classify-py compare test shell clean

build:
	docker compose build

generate:
	$(RUN) scripts/generate.sh $(PROFILE) $(COUNT) $(NAME)

classify-cpp:
	$(RUN) scripts/classify_cpp.sh $(NAME) $(CLASSIFIER)

classify-py:
	$(RUN) scripts/classify_py.sh $(NAME) $(ENGINE)

compare:
	$(RUN) scripts/classify_cpp.sh $(NAME) $(CLASSIFIER) -o data/$(NAME)/cpp_results.csv
	$(RUN) scripts/classify_py.sh $(NAME) $(ENGINE) --out data/$(NAME)/py_results.csv
	$(RUN) python3 pipeline/compare_results.py data/$(NAME)/cpp_results.csv data/$(NAME)/py_results.csv

test: generate classify-cpp classify-py

shell:
	$(RUN) bash

clean:
	rm -rf data/*/ network-packet-classification/build
