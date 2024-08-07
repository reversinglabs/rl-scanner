# rl-secure Docker image (rl-scanner)

This repository contains configurations used to create `rl-scanner` Docker images. To improve performance and reduce traffic, this image uses the cached install feature provided by the `rl-deploy` tool.

## Prerequisites

To create a cached installation file, you have to make sure that your license information is valid.

License information must be provided using the following environment variables:

| Environment variable | Description |
| :--------- | :------ |
| `RLSECURE_ENCODED_LICENSE` | Required. The `rl-secure` license file as a Base64-encoded string. Encode the contents of your license file, and provide the resulting string with this variable. |
| `RLSECURE_SITE_KEY` | Required. The `rl-secure` license site key. The site key is a string generated by ReversingLabs and sent to users with the license file. |


## Building the image

The `make` system is used to perform builds. 

To build an image, you can use one of the following build targets:

| Target name | Description |
| :--------- | :------ |
| `build-with-cache` | Generated image will use the installation cache mechanism. This will result in faster execution, since the scanner functionality will use a local cached installation instead of downloading updates from the ReversingLabs server. |
| `build-without-cache` | Generated image will contain only the scanner functionality. On each execution, the `rl-secure` tool will be downloaded from the ReversingLabs server. |


To locally build the scanner image, use the command:

```
make build-with-cache IMAGE_NAME="my-rl-scanner"
```

This will create an image with a tag `my-rl-scanner` using your local Docker instance.

Note that in order to make the `build-with-cache` target, you would need to provide the license information using the environment variables.


## Testing the image

To test the functionality of the image, you can use the `make` target named `test`.

In order to perform the test, it is expected that the environment variables `RLSECURE_ENCODED_LICENSE` and `RLSECURE_SITE_KEY` are set appropriately.

You can test the generated image with the following command:

```
make test IMAGE_NAME="my-rl-scanner"
```

## Release image

Documentation for using the generated image can be found [in the README](README.md).
