# reversinglabs/rl-scanner

![Header image](https://github.com/reversinglabs/rl-scanner/raw/main/armando-docker.png)

`reversinglabs/rl-scanner` is the official Docker image created by ReversingLabs for users who want to deploy the `rl-secure` solution in ephemeral environments and integrate it with their CI/CD tools.

To optimize the developer experience, the image provides helper tools that wrap commonly used `rl-secure` features - scanning packages and generating analysis reports.

This image is based on Rocky Linux 9.


## What is rl-secure?

`rl-secure` is a CLI tool that's part of the secure.software platform - a new ReversingLabs solution for software supply chain security.

With `rl-secure`, you can:

- Scan your software release packages on-premises and in your CI/CD pipelines to prevent threats from reaching production.
- Compare package versions to ensure no vulnerabilities are introduced in the open source libraries and third-party components you use.
- Prevent private keys, tokens, credentials and other sensitive information from leaking into production.
- Improve developer experience and ensure compliance with security best practices.
- Generate actionable analysis reports to help you prioritize and remediate issues in collaboration with your DevOps and security teams.


# Quick reference

**Maintained by:**

- [ReversingLabs](https://www.reversinglabs.com/) as part of the [secure.software platform](https://www.secure.software/)

**Where to get help:**

- [Official documentation](https://docs.secure.software/cli/)
- [ReversingLabs Support](mailto:support@reversinglabs.com)

**Where to file issues:**

- [GitHub repository](https://github.com/reversinglabs/rl-scanner/issues)


## Versioning and tags

Unversioned Docker image will have the tag `reversinglabs/rl-scanner:latest`.
This tag will always point to latest published image.

Versioned tags will be structured as `reversinglabs/rl-scanner:X`, where X is an incrementing version number. We will increment the major version number to signify a breaking change. If changes to the image are such that no existing functionality will be broken (small bug fixes or new helper tools), we will not increment the version number.

This makes it easier for cautious customers to use versioned tag images and migrate to a new version at their own convenience.


# How to use this image

The most common workflow for this Docker image is to scan a software package in a container and save the analysis report to local storage.
All input and output data is transferred into or out of the container using two (2) [Docker volume mounts](https://docs.docker.com/storage/volumes/).

The image provides a helper tool called `rl-scan` that wraps the `rl-secure` functionality into a practical script.
As a result, users don't have to chain multiple `rl-secure` commands in the container, as the whole workflow can be executed with a single `rl-scan` command.

To use the provided `rl-secure` functionality, a valid site-wide deployment license is required.
This type of license has two parts: the site key and the license file.
ReversingLabs sends both parts of the license to users on request.
Users must then encode the license file with the Base64 algorithm.
The Base64-encoded license string and the site key must be provided using [environment variables](#environment-variables).

When the container starts, it will try to download and install the latest version of `rl-secure`.
In some cases, a proxy server may be required to access the internet and connect to ReversingLabs servers.
This optional proxy configuration can be provided using environment variables.


## Prerequisites

To successfully use this Docker image, you need:

1. **A working Docker installation** on the system where you want to use the image. Follow [the official Docker installation instructions](https://docs.docker.com/engine/install/) for your platform.

2. **A valid rl-secure license with site key**. If you don't already have a site-wide deployment license, follow the instructions in [the official rl-secure documentation](https://docs.secure.software/cli/deployment/rl-deploy-quick-start#prepare-the-license-and-site-key) to get it from ReversingLabs. You don't need to activate the license - just save the license file and the site key for later use. You must convert your license file into a Base64-encoded string to use it with the Docker image.

3. **One or more software packages to analyze**. Your packages must be stored in a location that Docker will be able to access.


## Scan a file and generate analysis report

1. Prepare the file you want to scan and store it in a directory that will be mounted as your input (**package source** - read-only).

2. Prepare an empty directory where analysis reports will be stored after the file is scanned. That directory will be mounted as your output (**reports destination** - writable).

3. Start the container with input and output directories mounted as volumes and `rl-secure` license keys provided as environment variables.

To prevent issues with file ownership and access to analysis reports, the `-u` option is used to provide current user identification to the container.

The following command runs the `rl-scan` helper tool inside the container and scans a file from the mounted input directory.
The file must exist in the mounted input directory.
The tool will generate a report in the specified format (in this example, it's an HTML report) and save it to the mounted output directory.


```
docker run --rm \
  -u $(id -u):$(id -g) \
  -v "$(pwd)/packages:/packages:ro" \
  -v "$(pwd)/report:/report" \
  -e RLSECURE_ENCODED_LICENSE=<base64 encoded license file> \
  -e RLSECURE_SITE_KEY=<site key> \
  reversinglabs/rl-scanner \
  rl-scan --package-path=/packages/deployment_pkg.tgz --report-path=/report --report-format=rl-html
```


4. When the scan is complete, the container exits automatically. To confirm the file was successfully scanned, access the output directory (reports destination) and check if the analysis report is present.


## Configuration parameters

The `rl-scan` helper tool supports the following parameters.

| Parameter | Description |
| :--------- | :------ |
| `--package-path` | Required. Path to the package file you want to scan. The specified package file must exist in the **package source** directory mounted to the container.  |
| `--report-path` | Required. Path to the location where you want to store analysis reports. The specified path must exist in the **reports destination** directory mounted to the container. |
| `--report-format` | Required. A comma-separated list of report formats to generate. Supported values: `cyclonedx`, `sarif`, `rl-html`, `rl-json`, `all` |
| `--message-reporter` | Optional. Use it to change the format of output messages (STDOUT) for easier integration with CI tools. Supported values: `text`, `teamcity` |


## Environment variables

The following environment variables can be used with this image.

| Environment variable | Description |
| :--------- | :------ |
| `RLSECURE_ENCODED_LICENSE` | Required. The `rl-secure` license file as a Base64-encoded string. Users must encode the contents of your license file, and provide the resulting string with this variable. |
| `RLSECURE_SITE_KEY` | Required. The `rl-secure` license site key. The site key is a string generated by ReversingLabs and sent to users with the license file. |
| `RLSECURE_PROXY_SERVER` | Optional. Server URL for local proxy configuration. |
| `RLSECURE_PROXY_PORT` | Optional. Network port for local proxy configuration. |
| `RLSECURE_PROXY_USER` | Optional. User name for proxy authentication. |
| `RLSECURE_PROXY_PASSWORD` | Optional. Password for proxy authentication. |

