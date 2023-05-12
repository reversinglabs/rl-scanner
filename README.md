# rl-scanner


# Usage

This image provides a convenient way to use a subset of the functionality that the `rl-secure` package offers.
Common use case scenarios are optimized and offered as simple commands that are easy to integrate in the development pipeline.
A prerequisite to using this docker image is a valid license tied to a dedicated site key.

The included script expects a valid license provided to the Docker container through environment variables.
Since in an ephemeral configuration,
the license can not be issued to a dedicated machine,
it needs to be issued for a specified site key.
This means that the user needs to provide both the license key and the site key during the execution of the command.

The site key value is provided using the environment variable `RLSECURE_SITE_KEY`,
while the license file is provided using environment variable `RLSECURE_ENCODED_LICENSE`
The encoded license string is the result of encoding the license file using the Base64 algorithm.

On start of the docker image,
the latest version of the `rl-secure` package is downloaded and installed.
Additional environment variables exist to allow accessing the internet via a proxy in case that is required.

All input and output data is transferred into or out of the container using two (2) Docker volume mounts.


## rl-scan

`rl-scan` is the main entrypoint providing the `rl-secure` scan functionality.
It supports a simple use-case of scanning a single package and generating report(s).

In order to perform scan,
the user needs to provide the license information using environment variables:

| Mandatory Environment variable name | Description |
| ------------------------- | ----------- |
| RLSECURE_SITE_KEY | Site key string used for license |
| RLSECURE_ENCODED_LICENSE | License file encoded using Base64 encoding algorithm |

In case you would need to configure access to the internet via a proxy,
the configuration supports configuring the docker image to use a external proxy setup.

| Optional Environment variable name | Description |
| ------------------------- | ----------- |
| RLSECURE_PROXY_SERVER  | Proxy Server Host |
| RLSECURE_PROXY_PORT | Proxy Server Port |
| RLSECURE_PROXY_USER | Optional Proxy User |
| RLSECURE_PROXY_PASSWORD | Optional Proxy Password |

`rl-scan` allows the user to configure the scan using following parameters:

| Argument        | Description |
| --------------- | ----------- |
| `--package-path` | (input only) path to package file you want to scan |
| `--report-path` | (output only) path to location used to store final reports |
| `--report-format` | a comma-separated list of report formats to generate. Supported values: `cyclonedx`, `sarif`, `rl-html`, `rl-json`, `all` |
| `--message-reporter` | the format of output messages for easier integration into CI. Supported values: `text` and `teamcity` |


## Use case: Package scan with default configuration

This use case produces a `rl-secure` scan report(s) after scanning a single package file.
The scan is performed with the default configuration provided with the latest instance of `rl-secure`.

    docker run --rm \
        -u $(id -u):$(id -g) \
        -v "$(pwd)/packages:/packages:ro" \
        -v "$(pwd)/report:/report" \
        -e RLSECURE_ENCODED_LICENSE=<base64 encoded license file> \
        -e RLSECURE_SITE_KEY=<site key> \
        reversinglabs/rl-scanner \
            rl-scan \
                --package-path=/packages/deployment_pkg.tgz \
                --report-path=/report \
                --report-format=rl-html

with using proxy environment variables this would become:

    docker run --rm \
        -u $(id -u):$(id -g) \
        -v "$(pwd)/packages:/packages:ro" \
        -v "$(pwd)/report:/report" \
        -e RLSECURE_ENCODED_LICENSE=<base64 encoded license file> \
        -e RLSECURE_SITE_KEY=<site key> \
        -e RLSECURE_PROXY_SERVER=<proxy server host> \
        -e RLSECURE_PROXY_PORT=<proxy server port> \
        -e RLSECURE_PROXY_USER=<optional proxy server authentication user> \
        -e RLSECURE_PROXY_PASSWORD=<optional proxy server authentication password> \
        reversinglabs/rl-scanner \
            rl-scan \
                --package-path=/packages/deployment_pkg.tgz \
                --report-path=/report \
                --report-format=rl-html


In this example,
the directory `packages` is mounted read-only
as it will contain a file we will only read from during the scan (`deployment_pkg.tgz`)
the `report` directory is mounted as writable,
as the `rl-secure` report needs to be written into that directory.
We also provided a user identification to the container (`-u $(id -d):$(id -g)`)
to make sure that the report files will have the correct ownership after the scan has finished,
so we are able to access and delete them after processing.

## References
* For more info on `rl-secure` visit: https://www.secure.software/
