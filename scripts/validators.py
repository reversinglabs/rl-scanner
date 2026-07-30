import argparse
import glob
import os
import re
from urllib.parse import (
    parse_qs,
    urlsplit,
)

# https://docs.secure.software/cli/commands/scan#importing-files-from-urls
# npm: pkg:npm/react
# PyPI: pkg:pypi/pyaudio
# RubyGems: pkg:gem/CFPropertyList
# NuGet: pkg:nuget/mongodb.bson@2.30.0
# VS Code: pkg:vsx/redhat/vscode-yaml@1.13.0
# PS Gallery: pkg:psgallery/aws.tools.cloudwatch
# HuggingFace (Supported only in rl-secure CLI)	pkg:huggingface/gemma-3-270m-it@main


def validate_path_is_single_file(
    package_path: str,
) -> str:
    files = glob.glob(package_path, recursive=True)

    if len(files) > 1:
        raise RuntimeError(f"Path spec '{package_path}' resolves to more than one file!")

    if len(files) < 1:
        raise RuntimeError(f"Path spec '{package_path}' does not resolve to any file!")

    file: str = files[0]
    if os.path.isfile(file):
        return file
    raise RuntimeError(f"Path spec '{package_path}' does not resolve to a file!")


def validate_store_level_purl(
    params: argparse.Namespace,
) -> None:
    # if custom store is specified, PURL should be provided as well and level should not be used
    if params.rl_store is not None:
        if params.purl is None:
            raise RuntimeError("--purl must be specified when using an existing rl-store")
        if params.rl_level is not None:
            raise RuntimeError("--rl-store and --rl-level parameters can't be used together")


def validate_store_diff_purl(
    params: argparse.Namespace,
) -> None:
    # if diff is performed, PURL and store should be provided as well and rl-level is not compatible
    if params.diff_with is not None:
        if params.purl is None:
            raise RuntimeError("--purl should be specified when generating a difference report")
        if params.rl_store is None:
            raise RuntimeError("--rl-store should be specified when generating a difference report")


def validate_purl_repro_store(
    params: argparse.Namespace,
) -> None:
    if params.purl is not None:
        query = parse_qs(urlsplit(params.purl).query)
        if "build" in query and "repro" in query["build"]:
            if params.rl_store is None:
                raise RuntimeError("--rl-store must be specified when generating a reproducible build report")


def validate_report_path_exists_and_empty(
    params: argparse.Namespace,
) -> None:
    # if params.report_path object exists it should be an empty directory
    if os.path.exists(params.report_path) and not (
        os.path.isdir(params.report_path) and not os.listdir(params.report_path)
    ):
        raise RuntimeError("--report-path needs to point to an empty directory")


def validate_auth(
    params: argparse.Namespace,
) -> None:
    if params.bearer_token and (params.auth_user or params.auth_pass):
        msg = "--bearer-token cannot be used in combination with --auth-user or --auth-pass"
        raise RuntimeError(msg)


VALID_PARAMS: dict[str, dict[str, dict[str, str]]] = {
    "ALLOW": {
        "--import-url": {
            r"^https?://": "only http and https are currently supported",
        },
        "--import-docker": {
            r"^pkg:docker/": "only pkg:docker is supported",
        },
        "--import-purl": {
            r"^pkg:\w+/": "any pkg: except docker is supported",
            # unsupported ecosystems now fail at the scanner rather than at the CLI
        },
    },
    "DENY": {
        "--import-purl": {
            r"^pkg:docker/": "pkg:docker is not supported for --import-purl",
        },
    },
}


def validate_import_params(
    what: str,
    my_import: str,
) -> None:
    z = str(my_import).lower()  # we explicitly match lower as we are looking for the beginning only
    allow: dict[str, str] = VALID_PARAMS["ALLOW"].get(what, {})
    if allow:
        for k, v in allow.items():
            result = re.findall(k, z)
            if result == []:
                msg = f"{what} {v}"
                raise RuntimeError(msg)

    deny: dict[str, str] = VALID_PARAMS["DENY"].get(what, {})
    if deny:
        for k, v in deny.items():
            result = re.findall(k, z)
            if result != []:
                msg = f"{what} {v}"
                raise RuntimeError(msg)


def validate_import_url(
    params: argparse.Namespace,
) -> None:
    what = "--import-url"
    validate_import_params(
        what=what,
        my_import=params.import_url,
    )
    validate_auth(params=params)


def validate_import_purl(
    params: argparse.Namespace,
) -> None:
    what = "--import-purl"
    validate_import_params(
        what=what,
        my_import=params.import_purl,
    )
    validate_auth(params=params)


def validate_import_docker(
    params: argparse.Namespace,
) -> None:
    what = "--import-docker"
    validate_import_params(
        what=what,
        my_import=params.import_docker,
    )
    validate_auth(params=params)
