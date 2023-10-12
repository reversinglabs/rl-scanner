import os
import re
import glob
import shutil
import subprocess
from distutils.dir_util import copy_tree
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, urlunsplit, urlencode, SplitResult
from typing import (
    Optional,
    Any,
    List,
)

__INSTALL_LOCATION = "/tmp/__rlsecure"
__RLREPORT_LOCATION = "/tmp/__rlsecure-report"
__RLSTORE = "/tmp/__rlstore"


def __is_empty_dir(path: str) -> bool:
    return not any(Path(path).iterdir())


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


def use_store(store_path: str) -> None:
    global __RLSTORE
    __RLSTORE = store_path
    if not os.path.isdir(__RLSTORE):
        raise RuntimeError(f"'{__RLSTORE}' is not a directory")
    if not os.path.isdir(os.path.join(__RLSTORE, ".rl-secure")):
        init_store()


def init_store(level: Optional[str] = None) -> None:
    os.makedirs(__RLSTORE, exist_ok=True)
    if not __is_empty_dir(__RLSTORE):
        raise RuntimeError(f"'{__RLSTORE}' is not an empty directory")
    cmd = [__executable(), "init", __RLSTORE]
    if level is not None:
        cmd.append(f"--rl-level={level}")
    __run(cmd, check=True)


def __run_scan(args: List[str], **kwargs: Any) -> None:
    cmd = [__executable(), "scan", "--no-tracking", f"--rl-store={__RLSTORE}"]
    __run(cmd + args, **kwargs)


def scan(
    purl: str,
    path: str,
    replace: bool,
    base_version: Optional[str] = None,
) -> None:
    args = [f"--purl={purl}", f"--file-path={path}"]
    if replace:
        args.append("--replace")
    if base_version is not None:
        args.append(f"--sync-with={base_version}")
    __run_scan(args, check=True)


def prune(
    purl: str,
    before_date: Optional[str],
    after_date: Optional[str],
    days_older: Optional[int],
    hours_older: Optional[int],
) -> None:
    cmd = [__executable(), "prune", "--silent", f"--rl-store={__RLSTORE}", f"--purl={purl}"]
    if before_date is not None:
        cmd.append(f"--before-date={before_date}")
    if after_date is not None:
        cmd.append(f"--after-date={after_date}")
    if days_older is not None:
        cmd.append(f"--days-older={days_older}")
    if hours_older is not None:
        cmd.append(f"--hours-older={hours_older}")
    __run(cmd, check=True)


class ScanResult:
    def __init__(self, passed: bool, msg: str) -> None:
        self.passed = passed
        self.msg = msg


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

    purl_query = parse_qs(urlsplit(purl).query)
    is_repro = "build" in purl_query and "repro" in purl_query["build"]

    for report_dir in glob.iglob(os.path.join(__RLREPORT_LOCATION, "rl-html-diff-with-*")):
        if os.path.isdir(report_dir):
            os.rename(
                report_dir,
                os.path.join(__RLREPORT_LOCATION, "rl-html"),
            )
            break

    # copy report to desired location
    os.makedirs(rpt_path, exist_ok=True)
    copy_tree(__RLREPORT_LOCATION, rpt_path)

    # collect scan results
    if not is_repro:
        # normal scan
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
            return ScanResult(True, "rl-secure analysis: passed")

        if status.returncode > 0:
            msg = re.search(r"^\s*\[\s*CI:TEXT\s*\]\s*(.*)\s*$", status.stdout, re.MULTILINE)
            return ScanResult(False, msg.group(1) if msg is not None else "rl-secure analysis: failed")
    else:
        # repro scan
        def make_base_purl(purl):
            elements = urlsplit(purl)
            query = parse_qs(elements.query)
            del query["build"]
            return urlunsplit(
                SplitResult(elements.scheme, elements.netloc, elements.path, urlencode(query), elements.fragment)
            )

        base_purl = make_base_purl(purl)
        cmd = [
            __executable(),
            "checks",
            "--return-status",
            "--no-color",
            f"--purl={base_purl}",
            f"--rl-store={__RLSTORE}",
        ]
        status = __run(cmd, stdout=subprocess.PIPE, encoding="utf-8")

        if status.returncode == 3:
            return ScanResult(False, "reproducible build check: failed")

        if status.returncode >= 0:
            return ScanResult(True, "reproducible build check: passed")

    status.check_returncode()  # raise exception
    assert False  # to get rid of mypy no return code
