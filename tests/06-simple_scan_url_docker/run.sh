#!/bin/bash
set -e

DOCKER_IMAGE=$1

URL="https://hub.docker.com/layers/library/hello-world/latest/images/sha256-2771e37a12b7bcb2902456ecf3f29bf9ee11ec348e66e8eb322d9780ad7fc2df"

rm -rf report tmp
mkdir -p report tmp
docker run \
    --rm \
    -u $(id -u):$(id -g) \
    -v $(pwd)/report:/report \
    -e RLSECURE_ENCODED_LICENSE \
    -e RLSECURE_SITE_KEY \
    $DOCKER_IMAGE \
        rl-scan-url \
            --import-url="${URL}" \
            --report-path=/report \
            --pack-safe 2>&1 | tee ./tmp/out

python - << 'END_PYTHON'
import os.path
exitVal = 0
expectedFiles = [
    'report/rl-html/sdlc.html',
    'report/report.checks.json',
    'report/report.cve.csv',
    'report/report.cyclonedx.json',
    'report/report.rl.json',
    'report/report.sarif.json',
    'report/report.spdx.json',
    'report/report.rl-safe',
]
for f in expectedFiles:
    if not os.path.isfile(f):
        print("ERROR: Expected report not found: {}".format(f))
        exitVal = 1

exit(exitVal)
END_PYTHON
