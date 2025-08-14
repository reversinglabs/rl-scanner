from typing import (
    List,
)
import os
import glob
import argparse

from urllib.parse import (
    urlsplit,
    parse_qs,
)
from constants import VALID_PURL_TYPES


def validate_path_is_single_file(
    package_path: str,
) -> str:
    files = glob.glob(package_path, recursive=True)
    if len(files) > 1:
        raise RuntimeError(f'Path spec "{package_path}" resolves to more than one file!')
    if len(files) < 1:
        raise RuntimeError(f'Path spec "{package_path}" doesn\'t resolve to any file!')
    return files[0]


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


def validate_import_url(
    params: argparse.Namespace,
) -> None:
    if "://" not in params.import_url:
        raise RuntimeError("--import-url needs to be a url <proto>://<host>[:<port>]/<path>")

    z = params.import_url.lower()
    if not (z.startswith("http://") or z.startswith("https://")):
        raise RuntimeError("--import-url '<proto>://' must be http or https")

    if params.bearer_token and (params.auth_user or params.auth_pass):
        raise RuntimeError("--bearer-token cannot be used in combination with --auth-user or --auth-pass")


def validate_import_purl(
    params: argparse.Namespace,
) -> None:
    z = params.import_purl.lower()
    valid_start_purls: List[str] = VALID_PURL_TYPES
    valid = False
    for valid_start in valid_start_purls:
        if z.startswith(valid_start):
            valid = True
            break

    if valid is False:
        raise RuntimeError(f"--import purl currently supports only one of: {valid_start_purls}")

    if params.bearer_token and (params.auth_user or params.auth_pass):
        raise RuntimeError("--bearer-token cannot be used in combination with --auth-user or --auth-pass")
