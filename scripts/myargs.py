from typing import (
    List,
)
import argparse

from constants import REPORT_FORMATS


def my_common_prog_description(
    prog: str,
) -> str:
    return "\n".join(
        [
            f"ReversingLabs: {prog} CLI\n",
            "Extended product documentation is available at: https://docs.secure.software",
        ],
    )


def my_common_epilog() -> str:
    return "\n".join(
        [
            "Environment variables:",
            "  RLSECURE_ENCODED_LICENSE - Base64 encoded license file contents",
            "  RLSECURE_SITE_KEY        - Site activation key for licensing",
            "  RLSECURE_VAULT_KEY        - Password vault key",
            "  RLSECURE_PACKAGE_PASSWORD - Password used to scan package",
            "  RLSECURE_PROXY_SERVER    - Server URL for local proxy",
            "  RLSECURE_PROXY_PORT      - Network port for local proxy",
            "  RLSECURE_PROXY_USER      - User name for proxy authentication",
            "  RLSECURE_PROXY_PASSWORD  - Password for proxy authentication",
        ]
    )


def my_simple_epilog() -> str:
    return "\n".join(
        [
            "Environment variables:"
            "  RLSECURE_ENCODED_LICENSE - Base64 encoded license file contents"
            "  RLSECURE_SITE_KEY        - Site activation key for licensing"
            "  RLSECURE_PROXY_SERVER    - Server URL for local proxy"
            "  RLSECURE_PROXY_PORT      - Network port for local proxy"
            "  RLSECURE_PROXY_USER      - User name for proxy authentication"
            "  RLSECURE_PROXY_PASSWORD  - Password for proxy authentication",
        ],
    )


def params_basic(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--stream",
        required=False,
        help="Package stream name",
    )
    parser.add_argument(
        "--rl-store",
        required=False,
        help="Path to an existing rl-store",
    )
    parser.add_argument(
        "--vault-key",
        required=False,
        help="Password vault key",
    )
    parser.add_argument(
        "--purl",
        required=False,
        help="Package URL used for the scan (format [pkg:namespace/]<project></package><@version>)",
    )
    parser.add_argument(
        "--password",
        required=False,
        action="append",
        default=[],
        help="Specify the password that will be used to unpack password protected files. "
        + " Multiple passwords can be specified",
    )
    parser.add_argument(
        "--password-list",
        required=False,
        action="append",
        default=[],
        help="Specify the path to a password list that will be used when trying to unpack password protected files. "
        + "Multiple invocations are supported",
    )
    parser.add_argument(
        "--encoded-password-list",
        "--encoded-list",
        required=False,
        action="append",
        default=[],
        help="Base64 encoded password list file that will be used when trying to unpack password protected files."
        + " Multiple invocations are supported",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the existing package version within the rl-store",
    )
    parser.add_argument(
        "--diff-with",
        required=False,
        help="Previously analyzed package version to compare against the selected package",
    )
    parser.add_argument(
        "--rl-level",
        required=False,
        help="Specifies the rl-level used for the selected package scanning",
    )
    parser.add_argument(
        "--report-path",
        required=True,
        help="Path to a directory where the selected reports will be saved",
    )

    report_format_list: List[str] = list(REPORT_FORMATS.keys()) + ["all"]
    report_list = ", ".join(report_format_list)
    parser.add_argument(
        "--report-format",
        default="all",
        help=f"A comma-separated list of report formats to generate. Supported values: {report_list}",
    )
    parser.add_argument(
        "--message-reporter",
        choices=["teamcity", "text"],
        default="text",
        help="Processing status message format",
    )
    parser.add_argument(
        "--pack-safe",
        action="store_true",
        help="create a rl-safe archive in the report directory",
    )


def params_import_url(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--import-url",
        required=True,
        help="The URL you want to scan",
    )
    parser.add_argument(
        "--auth-user",
        help="specify the user, when downloading the url requires basic authentication ",
    )
    parser.add_argument(
        "--auth-pass",
        help="specify the password, when downloading the url requires basic authentication ",
    )
    parser.add_argument(
        "--bearer-token",
        help="specify the token, when downloading the url requires token based authentication ",
    )


def params_import_purl(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--import-purl",
        required=True,
        help="The PURL you want to scan",
    )
    parser.add_argument(
        "--auth-user",
        help="specify the user, when downloading the url requires basic authentication ",
    )
    parser.add_argument(
        "--auth-pass",
        help="specify the password, when downloading the url requires basic authentication ",
    )
    parser.add_argument(
        "--bearer-token",
        help="specify the token, when downloading the url requires token based authentication ",
    )


def params_import_docker(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--import-docker",
        required=True,
        help="The Docker package you want to scan",
    )
    parser.add_argument(
        "--auth-user",
        help="Specify the username for downloads from URLs that require basic authentication ",
    )
    parser.add_argument(
        "--auth-pass",
        help="Specify the password for downloads from URLs that require basic authentication ",
    )
    parser.add_argument(
        "--bearer-token",
        help="Specify the token for downloads from URLs that require token-based authentication ",
    )
