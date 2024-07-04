#!/bin/bash
set -e

DOCKER_IMAGE=$1

rm -rf report
mkdir -p report

docker run \
    --rm \
    -u $(id -u):$(id -g) \
    -v $(pwd):/package:ro \
    -v $(pwd)/report:/report \
    -e RLSECURE_ENCODED_LICENSE \
    -e RLSECURE_SITE_KEY \
    $DOCKER_IMAGE \
        rl-scan \
            --package-path=/package/sample.tgz \
            --report-path=/report

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
]
for f in expectedFiles:
    if not os.path.isfile(f):
        print("ERROR: Expected report not found: {}".format(f))
        exitVal = 1

exit(exitVal)
END_PYTHON
