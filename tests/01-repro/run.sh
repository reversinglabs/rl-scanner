#!/bin/bash
set -e

DOCKER_IMAGE=$1

rm -rf store report_*
mkdir -p store report_base report_repro_ok report_repro_fail

docker run \
    --rm \
    -u $(id -u):$(id -g) \
    -v $(pwd):/package:ro \
    -v $(pwd)/store:/store \
    -v $(pwd)/report_base:/report \
    -e RLSECURE_ENCODED_LICENSE \
    -e RLSECURE_SITE_KEY \
    $DOCKER_IMAGE \
        rl-scan \
            --rl-store=/store \
            --purl=package/project@base \
            --package-path=/package/repro_base.tgz \
            --report-path=/report

docker run \
    --rm \
    -u $(id -u):$(id -g) \
    -v $(pwd):/package:ro \
    -v $(pwd)/store:/store \
    -v $(pwd)/report_repro_ok:/report \
    -e RLSECURE_ENCODED_LICENSE \
    -e RLSECURE_SITE_KEY \
    $DOCKER_IMAGE \
        rl-scan \
            --rl-store=/store \
            --purl=package/project@base?build=repro \
            --package-path=/package/repro_ok.tgz \
            --report-path=/report

python - << 'END_PYTHON'
import os.path
exitVal = 0
expectedFiles = [
    'report_repro_ok/rl-html/sdlc.html',
    'report_repro_ok/report.cve.csv',
    'report_repro_ok/report.cyclonedx.json',
    'report_repro_ok/report.rl.json',
    'report_repro_ok/report.sarif.json',
    'report_repro_ok/report.spdx.json',
]
for f in expectedFiles:
    if not os.path.isfile(f):
        print("ERROR: Expected report not found: {}".format(f))
        exitVal = 1

exit(exitVal)
END_PYTHON

set +e
docker run \
    --rm \
    -u $(id -u):$(id -g) \
    -v $(pwd):/package:ro \
    -v $(pwd)/store:/store \
    -v $(pwd)/report_repro_fail:/report \
    -e RLSECURE_ENCODED_LICENSE \
    -e RLSECURE_SITE_KEY \
    $DOCKER_IMAGE \
        rl-scan \
            --rl-store=/store \
            --purl=package/project@base?build=repro \
            --replace \
            --package-path=/package/repro_fail.tgz \
            --report-path=/report

if [ $? -eq 0 ]
then
    echo "ERROR: Expected scan to fail"
    exit 1
fi
set -e

python - << 'END_PYTHON'
import os.path
exitVal = 0
expectedFiles = [
    'report_repro_fail/rl-html/sdlc.html',
    'report_repro_fail/report.cve.csv',
    'report_repro_fail/report.cyclonedx.json',
    'report_repro_fail/report.rl.json',
    'report_repro_fail/report.sarif.json',
    'report_repro_fail/report.spdx.json' ,
]
for f in expectedFiles:
    if not os.path.isfile(f):
        print("ERROR: Expected report not found: {}".format(f))
        exitVal = 1

exit(exitVal)
END_PYTHON
