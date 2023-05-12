#!/usr/bin/env python3


import os
import re
import shutil
import subprocess
from distutils.dir_util import copy_tree
from typing import (
    Optional,
    Any,
    List,
)

__INSTALL_LOCATION = "/tmp/__rlsecure"
__RLREPORT_LOCATION = "/tmp/__rlsecure-report"
__RLSTORE = "/tmp/__rlstore"


def __run(*args: Any, **kwargs: Any) -> Any:
    try:
        return subprocess.run(*args, **kwargs)
    except subprocess.CalledProcessError as ex:
        raise RuntimeError(f'Command "{" ".join(*args)}" returned non-zero exit code ({ex.returncode})') from ex
    except Exception as ex:
        raise RuntimeError(f'{str(ex)} while executing "{" ".join(*args)}"') from ex


def __executable() -> str:
    return os.path.join(__INSTALL_LOCATION, "rl-secure")


def check_if_installed() -> bool:
    return os.access(__executable(), os.X_OK)


def __collect_install_arg(arg_name: str, env_var_name: str) -> Optional[str]:
    env_var = os.environ.get(env_var_name)
    return f"--{arg_name}={env_var}" if env_var is not None else None


def __collect_install_args() -> List[str]:
    arg_defs = [
        ("encoded-key", "RLSECURE_ENCODED_LICENSE"),
        ("site-key", "RLSECURE_SITE_KEY"),
        ("proxy-server", "RLSECURE_PROXY_SERVER"),
        ("proxy-port", "RLSECURE_PROXY_PORT"),
        ("proxy-user", "RLSECURE_PROXY_USER"),
        ("proxy-password", "RLSECURE_PROXY_PASSWORD"),
    ]
    args = [__collect_install_arg(a[0], a[1]) for a in arg_defs]
    return [a for a in args if a is not None]


def install() -> None:
    args = ["rl-deploy", "install", __INSTALL_LOCATION, "--no-tracking"] + __collect_install_args()
    __run(args, check=True)


def init_store() -> None:
    os.makedirs(__RLSTORE)
    __run([__executable(), "init", __RLSTORE], check=True)


def __run_scan(args: List[str], **kwargs: Any) -> None:
    cmd = [__executable(), "scan", "--no-tracking", f"--rl-store={__RLSTORE}"]
    __run(cmd + args, **kwargs)


def scan(purl: str, path: str) -> None:
    __run_scan([f"--purl={purl}", f"--file-path={path}"], check=True)


class ScanResult:
    def __init__(self, passed: bool, msg: str) -> None:
        self.passed = passed
        self.msg = msg
        return


def generate_report(
    purl: str,
    rpt_path: str,
    rpt_format: str,
    base_version: Optional[str] = None,
) -> ScanResult:
    shutil.rmtree(__RLREPORT_LOCATION, ignore_errors=True)
    os.makedirs(__RLREPORT_LOCATION, exist_ok=True)

    cmd = [
        __executable(),
        "report",
        rpt_format,
        "--no-tracking",
        f"--purl={purl}",
        f"--rl-store={__RLSTORE}",
        f"--output-path={__RLREPORT_LOCATION}",
    ]
    if base_version is not None:
        cmd.append(f"--diff-with={base_version}")
    __run(cmd, check=True)

    if base_version is not None:
        os.rename(
            os.path.join(__RLREPORT_LOCATION, f"rl-html-diff-with-{base_version}"),
            os.path.join(__RLREPORT_LOCATION, "rl-html"),
        )

    # copy report to desired location
    os.makedirs(rpt_path, exist_ok=True)
    copy_tree(__RLREPORT_LOCATION, rpt_path)

    # collect scan results
    cmd = [
        __executable(),
        "status",
        "--return-status",
        "--no-color",
        f"--purl={purl}",
        f"--rl-store={__RLSTORE}",
    ]
    status = __run(cmd, stdout=subprocess.PIPE, encoding="utf-8")

    if status.returncode == 0:
        return ScanResult(True, "rl-secure analysis: completed")

    if status.returncode > 0:
        msg = re.search(r"^\s*\[\s*CI:TEXT\s*\]\s*(.*)\s*$", status.stdout, re.MULTILINE)
        return ScanResult(False, msg.group(1) if msg is not None else "rl-secure analysis: failed")

    status.check_returncode()  # raise exception
    assert False  # to get rid of mypy no return code
