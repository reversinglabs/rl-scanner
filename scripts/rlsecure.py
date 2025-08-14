from typing import (
    Optional,
    Any,
    List,
    Tuple,
)
import os
import re
import glob
import uuid
import shutil
import subprocess
import argparse
from pathlib import Path
from urllib.parse import (
    urlsplit,
    parse_qs,
    urlunsplit,
    urlencode,
    SplitResult,
)
from dataclasses import (
    dataclass,
    field,
)
from constants import (
    RL_SAFE_FORMAT_LIST,
    CACHE_LOCATION,
    INSTALL_LOCATION,
    RLREPORT_LOCATION,
    RLSTORE,
    VAULT_KEY,
)
from cimessages import Messages

__CACHE_LOCATION: str = CACHE_LOCATION
__INSTALL_LOCATION: str = INSTALL_LOCATION
__RLREPORT_LOCATION: str = RLREPORT_LOCATION
__RLSTORE: str = RLSTORE
__VAULT_KEY: Optional[str] = VAULT_KEY

RlSafeFormatList: List[str] = RL_SAFE_FORMAT_LIST


@dataclass
class PkgPasswords:
    passwords: List[str] = field(default_factory=list)
    encoded_passwords: List[str] = field(default_factory=list)
    password_lists: List[str] = field(default_factory=list)

    def empty(self) -> bool:
        return len(self.passwords) == 0 and len(self.encoded_passwords) == 0 and len(self.password_lists) == 0

    def cmd_args(self) -> List[str]:
        cmd = []
        cmd += [f"--password={p}" for p in self.passwords]
        cmd += [f"--password-list={p}" for p in self.password_lists]
        cmd += [f"--encoded-list={p}" for p in self.encoded_passwords]
        return cmd


class ScanResult:  # pylint: disable=too-few-public-methods
    def __init__(self, passed: bool, msg: str) -> None:
        self.passed = passed
        self.msg = msg


def __is_empty_dir(
    path: str,
) -> bool:
    return not any(Path(path).iterdir())


def __executable(
    what: str = "rl-secure",
) -> str:
    assert what in ["rl-secure", "rl-safe"]
    return os.path.join(__INSTALL_LOCATION, what)


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


def __collect_install_arg(
    arg_name: str,
    env_var_name: str,
) -> Optional[str]:
    env_var = os.environ.get(env_var_name)
    return f"--{arg_name}={env_var}" if env_var is not None else None


def __run(
    *args: Any,
    **kwargs: Any,
) -> Any:
    def sanitize_arg(arg: str) -> str:
        if arg.startswith("--vault-key="):
            return "--vault-key=***"
        if arg.startswith("--password="):
            return "--password=***"
        if arg.startswith("--encoded-list="):
            return "--encoded-list=***"
        return arg

    try:
        return subprocess.run(
            *args,
            **kwargs,
        )  # pylint: disable=subprocess-run-check
    except subprocess.CalledProcessError as ex:
        raise RuntimeError(
            f'Command "{" ".join(map(sanitize_arg, *args))}" returned non-zero exit code ({ex.returncode})'
        ) from ex
    except Exception as ex:
        raise RuntimeError(f'{str(ex)} while executing "{" ".join(map(sanitize_arg, *args))}"') from ex


def __print_version() -> None:
    args = [
        __executable("rl-secure"),
        "--version",
    ]

    __run(args, check=True)


def __run_scan(
    args: List[str],
    **kwargs: Any,
) -> None:
    cmd = [
        __executable("rl-secure"),
        "scan",
        "--no-tracking",
    ] + _store_cmd_args()

    __run(cmd + args, **kwargs)

    __print_version()


def _prep_report_location() -> None:
    shutil.rmtree(__RLREPORT_LOCATION, ignore_errors=True)
    os.makedirs(__RLREPORT_LOCATION, exist_ok=True)


def _post_reports_copy(report_path: str) -> None:

    # copy report to desired location
    os.makedirs(report_path, exist_ok=True)
    shutil.copytree(
        src=__RLREPORT_LOCATION,
        dst=report_path,
        dirs_exist_ok=True,
    )


def _do_reports(
    purl: str,
    report_format: str,
    diff_with: Optional[str] = None,  # diff_with
) -> None:

    cmd = [
        __executable("rl-secure"),
        "report",
        report_format,
        "--no-tracking",
        f"--purl={purl}",
        f"--rl-store={__RLSTORE}",
        f"--output-path={__RLREPORT_LOCATION}",
    ]
    if diff_with is not None:
        cmd.append(f"--diff-with={diff_with}")

    __run(cmd, check=True)

    for report_dir in glob.iglob(os.path.join(__RLREPORT_LOCATION, "rl-html-diff-with-*")):
        if os.path.isdir(report_dir):
            os.rename(
                report_dir,
                os.path.join(__RLREPORT_LOCATION, "rl-html"),
            )
            break


def _reduce_reports_to_pack(
    report_format: str,
) -> str:
    a: List[str] = report_format.split(",")
    # split report_format on ','
    # remove all invalid items
    # return join with ','
    b: List[str] = []
    for item in a:
        if item in RlSafeFormatList:
            b.append(item)
    return ",".join(b)


def _do_pack_safe(
    purl: str,
    report_format: str,
    diff_with: Optional[str] = None,
) -> None:
    pack_format = _reduce_reports_to_pack(report_format)
    cmd = [
        __executable("rl-safe"),
        "pack",
        f"--purl={purl}",
        f"--rl-store={__RLSTORE}",
        f"--format={pack_format}",
        f"--output-path={__RLREPORT_LOCATION}",
        "--no-tracking",
    ]
    if diff_with is not None:
        cmd.append(f"--diff-with={diff_with}")

    __run(cmd, check=True)


def _do_status(
    purl: str,
) -> ScanResult:
    # normal scan
    cmd = [
        __executable("rl-secure"),
        "status",
        "--return-status",
        "--no-color",
        f"--purl={purl}",
        f"--rl-store={__RLSTORE}",
    ]

    status = __run(
        cmd,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )

    if status.returncode == 0:
        return ScanResult(True, "rl-secure analysis: passed")

    if status.returncode > 0:
        msg = re.search(r"^\s*\[\s*CI:TEXT\s*\]\s*(.*)\s*$", status.stdout, re.MULTILINE)
        return ScanResult(False, msg.group(1) if msg is not None else "rl-secure analysis: failed")

    status.check_returncode()  # raise exception
    assert False  # to get rid of mypy no return code


def _do_checks(
    purl: str,
) -> ScanResult:
    # repro scan
    def make_base_purl(purl: str) -> str:
        elements = urlsplit(purl)
        query = parse_qs(elements.query)
        del query["build"]
        return urlunsplit(
            SplitResult(
                elements.scheme,
                elements.netloc,
                elements.path,
                urlencode(query),
                elements.fragment,
            )
        )

    base_purl = make_base_purl(purl)
    cmd = [
        __executable("rl-secure"),
        "checks",
        "--return-status",
        "--no-color",
        f"--purl={base_purl}",
        f"--rl-store={__RLSTORE}",
    ]
    status = __run(
        cmd,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )

    if status.returncode == 3:
        return ScanResult(False, "reproducible build check: failed")

    if status.returncode >= 0:
        return ScanResult(True, "reproducible build check: passed")

    status.check_returncode()  # raise exception
    assert False  # to get rid of mypy no return code


def _do_scan_results(purl: str) -> ScanResult:
    # collect scan results
    purl_query = parse_qs(urlsplit(purl).query)
    is_repro = "build" in purl_query and "repro" in purl_query["build"]

    if not is_repro:
        return _do_status(purl)

    return _do_checks(purl)


def _vault_init(
    vault_key: str,
) -> None:
    cmd = [
        __executable("rl-secure"),
        "vault",
        "init",
        f"--vault-key={vault_key}",
    ] + _store_cmd_args()
    __run(cmd, check=True)

    global __VAULT_KEY  # pylint: disable=global-statement
    __VAULT_KEY = vault_key


def _store_cmd_args() -> List[str]:
    cmd = [f"--rl-store={__RLSTORE}"]
    if __VAULT_KEY is not None:
        cmd.append(f"--vault-key={__VAULT_KEY}")
    return cmd


def _scan_item(
    *,
    what: str,  # file, url, purl, later: docker
    item: str,
    passwords: PkgPasswords,
    params: argparse.Namespace,
) -> None:
    purl: str = params.purl
    replace: bool = params.replace
    diff_with: Optional[str] = params.diff_with

    assert len(item) > 0
    assert what in ["file", "url", "purl"]

    args = [
        f"--purl={purl}",
        f"--file-path={item}",
    ]

    if replace:
        args.append("--replace")

    if diff_with is not None:
        args.append(f"--sync-with={diff_with}")

    args += passwords.cmd_args()

    __run_scan(args, check=True)


def _generate_report(
    *,
    params: argparse.Namespace,
) -> ScanResult:
    purl: str = params.purl
    report_path: str = params.report_path
    report_format: str = params.report_format
    diff_with: Optional[str] = params.diff_with
    pack_safe: bool = params.pack_safe

    _prep_report_location()

    _do_reports(
        purl,
        report_format,
        diff_with,
    )

    if pack_safe:
        _do_pack_safe(
            purl,
            report_format,
            diff_with,
        )

    _post_reports_copy(
        report_path,
    )

    return _do_scan_results(purl)


def _install_and_init_rlsecure(
    params: argparse.Namespace,
    reporter: Messages,
    vault_key: Optional[str] = None,
) -> None:
    if not check_if_installed("rl-secure"):
        with reporter.progress_block("Installing rl-secure"):
            install(
                stream=params.stream,
            )

    # set rl-store
    if params.rl_store is not None:
        use_store(
            store_path=params.rl_store,
        )
        return

    # initialize temporary store
    with reporter.progress_block("Initializing rl-secure store"):
        _init_store(
            level=params.rl_level,
            vault_key=vault_key,
        )


def _init_store(
    *,
    level: Optional[str] = None,
    vault_key: Optional[str] = None,
) -> None:

    os.makedirs(__RLSTORE, exist_ok=True)
    if not __is_empty_dir(__RLSTORE):
        raise RuntimeError(f"'{__RLSTORE}' is not an empty directory")

    cmd = [
        __executable("rl-secure"),
        "init",
    ] + _store_cmd_args()

    if level is not None:
        cmd.append(f"--rl-level={level}")

    __run(cmd, check=True)

    if vault_key is not None:
        _vault_init(vault_key)


# PUBLIC


def collect_password_info(
    params: argparse.Namespace,
) -> Tuple[PkgPasswords, Optional[str]]:

    # collect password information
    passwords = read_package_password_parameters(params)
    vault_key = None

    # if internal store is used,
    # we can use fixed vault password since store is temporary
    if params.rl_store is None:
        vault_key = str(uuid.uuid4())
    else:
        if os.environ.get("RLSECURE_VAULT_KEY") is not None:
            vault_key = os.environ.get("RLSECURE_VAULT_KEY")

        if params.vault_key is not None:
            vault_key = params.vault_key

    if not passwords.empty() and vault_key is None:
        raise RuntimeError("vault key should be specified if package password is used")

    return passwords, vault_key


def check_if_installed(what: str) -> bool:
    return os.access(__executable(what=what), os.X_OK)


def install(
    *,
    stream: Optional[str] = None,
) -> None:
    args = [
        "rl-deploy",
        "install",
        __INSTALL_LOCATION,
        "--no-tracking",
    ]
    if os.path.isfile(__CACHE_LOCATION):
        args.append(f"--from-cache={__CACHE_LOCATION}")

    args += __collect_install_args()
    if stream is not None:
        args.append(f"--stream={stream}")

    __run(args, check=True)


def use_store(
    *,
    store_path: str,
    vault_key: Optional[str] = None,
) -> None:
    global __RLSTORE  # pylint: disable=global-statement
    __RLSTORE = store_path

    global __VAULT_KEY  # pylint: disable=global-statement
    __VAULT_KEY = vault_key

    if not os.path.isdir(__RLSTORE):
        raise RuntimeError(f"'{__RLSTORE}' is not a directory")

    if not os.path.isdir(os.path.join(__RLSTORE, ".rl-secure")):
        _init_store()


def read_package_password_parameters(
    args: Any,
) -> PkgPasswords:
    pwds = PkgPasswords()

    # collect environment variables
    def collect_pass(passwords: List[str], env_var_name: str, arg_name: str) -> None:
        env = os.environ.get(env_var_name)
        if env is not None:
            passwords.append(env)
        arg = getattr(args, arg_name, [])
        if arg is not None and len(arg) > 0:
            passwords.extend(arg)

    collect_pass(pwds.passwords, "RLSECURE_PACKAGE_PASSWORD", "password")
    collect_pass(pwds.encoded_passwords, "RLSECURE_PACKAGE_ENCODED_LIST", "encoded_password_list")
    collect_pass(pwds.password_lists, "RLSECURE_PACKAGE_PASSWORD_LIST", "password_list")

    return pwds


def prune(
    *,
    purl: str,
    before_date: Optional[str],
    after_date: Optional[str],
    days_older: Optional[int],
    hours_older: Optional[int],
) -> None:
    cmd = [
        __executable("rl-secure"),
        "prune",
        "--silent",
        f"--rl-store={__RLSTORE}",
        f"--purl={purl}",
    ]

    if before_date is not None:
        cmd.append(f"--before-date={before_date}")

    if after_date is not None:
        cmd.append(f"--after-date={after_date}")

    if days_older is not None:
        cmd.append(f"--days-older={days_older}")

    if hours_older is not None:
        cmd.append(f"--hours-older={hours_older}")

    __run(cmd, check=True)


def do_init_scanfile_report_status(
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: Optional[str] = None,
) -> int:
    # VERIFY INSTALL OK
    _install_and_init_rlsecure(
        params,
        reporter,
        vault_key,
    )

    # SCAN
    with reporter.progress_block("Scanning software package"):
        reporter.info(f"Package path: {params.package_path}")

        _scan_item(
            what="file",
            item=params.package_path,
            passwords=passwords,
            params=params,
        )

    # REPORT
    # generate report
    # testing: params.pack_safe = True
    with reporter.progress_block("Generating report(s)"):
        result = _generate_report(
            params=params,
        )

        # STATUS
        should_report_result = reporter.scan_result(
            result.passed,
            result.msg,
        )
        if should_report_result:
            if result.passed:
                return 0
            else:
                return 1

    return 0


def do_init_scanurl_report_status(
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: Optional[str] = None,
) -> int:
    # VERIFY INSTALL OK
    _install_and_init_rlsecure(
        params,
        reporter,
        vault_key,
    )

    # SCAN
    with reporter.progress_block("Scanning software package"):
        reporter.info(f"Package path: {params.import_url}")

        _scan_item(
            what="url",
            item=params.import_url,
            passwords=passwords,
            params=params,
        )

    # REPORT
    # generate report
    # testing: params.pack_safe = True
    with reporter.progress_block("Generating report(s)"):
        result = _generate_report(
            params=params,
        )

        # STATUS
        should_report_result = reporter.scan_result(
            result.passed,
            result.msg,
        )
        if should_report_result:
            if result.passed:
                return 0
            else:
                return 1

    return 0


def do_init_scanpurl_report_status(
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: Optional[str] = None,
) -> int:
    # VERIFY INSTALL OK
    _install_and_init_rlsecure(
        params,
        reporter,
        vault_key,
    )

    # SCAN
    with reporter.progress_block("Scanning software package"):
        reporter.info(f"Package path: {params.import_purl}")

        _scan_item(
            what="purl",
            item=params.import_purl,
            passwords=passwords,
            params=params,
        )

    # REPORT
    # generate report
    # testing: params.pack_safe = True
    with reporter.progress_block("Generating report(s)"):
        result = _generate_report(
            params=params,
        )

        # STATUS
        should_report_result = reporter.scan_result(
            result.passed,
            result.msg,
        )
        if should_report_result:
            if result.passed:
                return 0
            else:
                return 1

    return 0
