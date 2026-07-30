import argparse
import glob
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    Any,
)
from urllib.parse import (
    SplitResult,
    parse_qs,
    urlencode,
    urlsplit,
    urlunsplit,
)

from cimessages import Messages
from constants import (
    CACHE_LOCATION,
    INSTALL_LOCATION,
    RL_SAFE_FORMAT_LIST,
    RLREPORT_LOCATION,
    TMP_DIR,
)


@dataclass
class PkgPasswords:
    passwords: list[str] = field(default_factory=list)
    encoded_passwords: list[str] = field(default_factory=list)
    password_lists: list[str] = field(default_factory=list)

    def empty(self) -> bool:
        return len(self.passwords) == 0 and len(self.encoded_passwords) == 0 and len(self.password_lists) == 0

    def cmd_args(self) -> list[str]:
        cmd = []
        cmd += [f"--password={p}" for p in self.passwords]
        cmd += [f"--password-list={p}" for p in self.password_lists]
        cmd += [f"--encoded-list={p}" for p in self.encoded_passwords]
        return cmd


class ScanResult:  # pylint: disable=too-few-public-methods
    def __init__(self, passed: bool, msg: str) -> None:
        self.passed = passed
        self.msg = msg


# ----------------------------------------------------
# globals start
_rl_store_: str = f"{TMP_DIR}/__rlstore"  # initial
_vault_key_: str | None = None  # initial no key


def get_store() -> str:
    return _rl_store_


def set_store(store_path: str) -> None:
    global _rl_store_

    if not os.path.isdir(store_path):
        raise RuntimeError(f"'{store_path}' is not a directory")

    _rl_store_ = store_path


def get_vault_key() -> str | None:
    return _vault_key_


def set_vault_key_if_present(vault_key: str | None = None) -> None:
    global _vault_key_
    if vault_key:
        _vault_key_ = vault_key


# globals end
# ----------------------------------------------------


def _rl_secure_init(store: str, level: int | None = None) -> None:
    cmd: list[str] = [
        __executable("rl-secure"),
        "init",
        f"--rl-store={store}",
    ]

    if level is not None:  # can be 0 - 4
        cmd.append(f"--rl-level={level}")

    __run(cmd, check=True)


def _rl_secure_vault_init(store: str, vault_key: str) -> None:
    cmd: list[str] = [
        __executable("rl-secure"),
        "vault",
        "init",
        f"--rl-store={store}",
        f"--vault-key={vault_key}",
    ]

    __run(cmd, check=True)


def _install_and_init_rlsecure(
    params: argparse.Namespace,
    reporter: Messages,
    vault_key: str | None = None,
) -> None:
    set_vault_key_if_present(vault_key)

    # allways first install rl-secure if we dont have it yet
    if not check_if_installed("rl-secure"):
        with reporter.progress_block("Installing rl-secure"):
            install(stream=params.stream)

    # use the specified store when specified
    if params.rl_store:
        set_store(params.rl_store)

    store = get_store()
    vault_key = get_vault_key()

    # if the store was not initialized or does not exist at all init one
    if not os.path.isdir(os.path.join(store, ".rl-secure")):
        with reporter.progress_block("Initializing rl-secure store"):
            level: int | None = None
            if getattr(params, "rl_level", None) is not None:
                level = params.rl_level

            os.makedirs(store, exist_ok=True)
            if not __is_empty_dir(store):
                raise RuntimeError(f"'{store}' is not an empty directory")

            _rl_secure_init(store, level)
            if vault_key:
                _rl_secure_vault_init(store, vault_key)


def __is_empty_dir(
    path: str,
) -> bool:
    return not any(Path(path).iterdir())


def __executable(
    what: str = "rl-secure",
) -> str:
    valid_what = ["rl-secure", "rl-safe"]
    if what not in valid_what:
        msg = f"{what} is not supported; valid is: {valid_what}"
        raise RuntimeError(msg)

    return os.path.join(INSTALL_LOCATION, what)


def __collect_install_env_args() -> list[str]:
    arg_defs = [
        ("encoded-key", "RLSECURE_ENCODED_LICENSE"),
        ("site-key", "RLSECURE_SITE_KEY"),
        ("proxy-server", "RLSECURE_PROXY_SERVER"),
        ("proxy-port", "RLSECURE_PROXY_PORT"),
        ("proxy-user", "RLSECURE_PROXY_USER"),
        ("proxy-password", "RLSECURE_PROXY_PASSWORD"),
    ]
    args = [__collect_install_env_arg(a[0], a[1]) for a in arg_defs]
    return [a for a in args if a is not None]


def __collect_install_env_arg(
    arg_name: str,
    env_var_name: str,
) -> str | None:
    env_var = os.environ.get(env_var_name)
    if env_var is None:
        return None
    if len(env_var) == 0:
        return None
    return f"--{arg_name}={env_var}"


BLOCK_LIST: list[str] = [
    "--vault-key=",
    "--password=",
    "--encoded-list=",
    "--encoded-key=",
    "--proxy-password=",
    "--site-key=",
    "--auth-pass=",
    "--bearer-token=",
]


def _sanitize_args(args: list[str]) -> list[str]:
    return [_sanitize_arg(a) for a in args]


def _sanitize_arg(arg: str) -> str:
    for item in BLOCK_LIST:
        if arg.startswith(item):
            return f"{item}***"
    return arg


def __run(
    args: list[str],
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    clean: list[str] = _sanitize_args(args)
    feedback = " ".join(clean)

    kwargs.setdefault("timeout", 3600 * 5)
    kwargs.setdefault("encoding", "utf-8")

    try:
        return subprocess.run(args, **kwargs)

    except subprocess.CalledProcessError as ex:
        msg = f'Command "{feedback}" returned non-zero exit code ({ex.returncode})'
        raise RuntimeError(msg) from None

    except Exception as ex:
        msg = f'{str(ex)} while executing command "{feedback}"'
        raise RuntimeError(msg) from None


def __print_version() -> None:
    args: list[str] = [
        __executable("rl-secure"),
        "--version",
    ]

    __run(args, check=True)


def __run_scan(
    args: list[str],
    **kwargs: Any,
) -> None:
    store = get_store()

    cmd: list[str] = [
        __executable("rl-secure"),
        "scan",
        "--no-tracking",
        f"--rl-store={store}",
    ]

    vault_key = get_vault_key()
    if vault_key:
        cmd.append(f"--vault-key={vault_key}")

    __run(cmd + args, **kwargs)
    __print_version()


def _prep_report_location() -> None:
    shutil.rmtree(RLREPORT_LOCATION, ignore_errors=True)
    os.makedirs(RLREPORT_LOCATION, exist_ok=True)


def _post_reports_copy(report_path: str) -> None:
    # copy report to desired location
    os.makedirs(report_path, exist_ok=True)
    shutil.copytree(
        src=RLREPORT_LOCATION,
        dst=report_path,
        dirs_exist_ok=True,
    )


def _do_reports(
    purl: str,
    report_format: str,
    diff_with: str | None = None,  # diff_with
) -> None:
    store = get_store()

    cmd: list[str] = [
        __executable("rl-secure"),
        "report",
        report_format,
        "--no-tracking",
        f"--purl={purl}",
        f"--rl-store={store}",
        f"--output-path={RLREPORT_LOCATION}",
    ]
    if diff_with is not None:
        cmd.append(f"--diff-with={diff_with}")

    __run(cmd, check=True)

    for report_dir in glob.iglob(os.path.join(RLREPORT_LOCATION, "rl-html-diff-with-*")):
        if os.path.isdir(report_dir):
            os.rename(
                report_dir,
                os.path.join(RLREPORT_LOCATION, "rl-html"),
            )
            break


def _reduce_reports_to_pack(
    report_format: str,
) -> str:
    a: list[str] = report_format.split(",")
    # split report_format on ','
    # remove all invalid items
    # return join with ','
    b: list[str] = []
    for item in a:
        if item in RL_SAFE_FORMAT_LIST:
            b.append(item)
    return ",".join(b)


def _do_pack_safe(
    purl: str,
    report_format: str,
    diff_with: str | None = None,
) -> None:
    pack_format = _reduce_reports_to_pack(report_format)
    # pack_format could be empty list
    store = get_store()

    cmd: list[str] = [
        __executable("rl-safe"),
        "pack",
        f"--purl={purl}",
        f"--rl-store={store}",
        f"--output-path={RLREPORT_LOCATION}",
        "--no-tracking",
    ]
    if len(pack_format):
        cmd.append(f"--format={pack_format}")

    if diff_with is not None:
        cmd.append(f"--diff-with={diff_with}")

    __run(cmd, check=True)


def _do_status(
    purl: str,
) -> ScanResult:
    # normal scan
    store = get_store()

    cmd: list[str] = [
        __executable("rl-secure"),
        "status",
        "--return-status",
        "--no-color",
        f"--purl={purl}",
        f"--rl-store={store}",
    ]

    status = __run(
        cmd,
        stdout=subprocess.PIPE,
    )

    if status.returncode == 0:
        return ScanResult(True, "rl-secure analysis: passed")

    if status.returncode > 0:
        msg = re.search(r"^\s*\[\s*CI:TEXT\s*\]\s*(.*)\s*$", status.stdout, re.MULTILINE)
        return ScanResult(False, msg.group(1) if msg is not None else "rl-secure analysis: failed")

    status.check_returncode()  # raise exception
    raise AssertionError("false")  # to get rid of mypy no return code


def _do_checks(
    purl: str,
) -> ScanResult:
    def make_base_purl(purl: str) -> str:
        elements = urlsplit(purl)

        query = parse_qs(elements.query)
        if "build" in query:
            del query["build"]

        return urlunsplit(
            SplitResult(  # SplitResult(scheme, netloc, path, query, fragment)
                elements.scheme,
                elements.netloc,
                elements.path,
                urlencode(query, doseq=True),
                elements.fragment,
            )
        )

    base_purl = make_base_purl(purl)
    store = get_store()

    cmd: list[str] = [
        __executable("rl-secure"),
        "checks",
        "--return-status",
        "--no-color",
        f"--purl={base_purl}",
        f"--rl-store={store}",
    ]

    status = __run(
        cmd,
        stdout=subprocess.PIPE,
    )

    # https://docs.secure.software/cli/commands/checks
    # Every check type is assigned a label that shows the status information (pass or fail) for the check.
    # The first two characters in the label are used to distinguish between check types:
    # L(n) - software package analysis with SAFE Levels enabled
    # CI - software package analysis with SAFE Levels disabled
    # C(n) - software package analysis with custom SAFE Levels
    # DF - comparison (diff) between package version artifacts
    # RB - reproducible build check
    #
    # Return status as exit code.
    # This is useful when working with CI/CD.
    # The following exit codes are supported:
    # 0 - PASS,
    # 1 - CI:FAIL,
    # 2 - DF:FAIL,
    # 3 - RB:FAIL

    code = status.returncode
    if code == 0:
        return ScanResult(True, "reproducible build check: passed")

    if code in [1, 2, 3]:
        return ScanResult(False, "reproducible build check: failed")

    status.check_returncode()  # raise exception
    raise AssertionError("false")  # to get rid of mypy no return code


def _do_scan_results(purl: str) -> ScanResult:
    # collect scan results
    purl_query = parse_qs(urlsplit(purl).query)
    is_repro = "build" in purl_query and "repro" in purl_query["build"]

    if not is_repro:
        return _do_status(purl)

    return _do_checks(purl)


def _scan_item(
    *,
    what: str,
    item: str,
    passwords: PkgPasswords,
    params: argparse.Namespace,
) -> None:
    valid_what = ["file", "url", "purl", "docker"]

    if what not in valid_what:
        msg = f"{what} is not supported; valid is: {valid_what}"
        raise RuntimeError(msg)

    if len(item) == 0:
        msg = f"{what}: item provided has length 0"
        raise RuntimeError(msg)

    args = [
        f"--purl={params.purl}",  # is purl, not the item we are scanning but the purl we will store the results under
        f"--file-path={item}",  # hint: is correct for file, url, purl and docker args
    ]

    if what != "file":
        if getattr(params, "bearer_token", None):
            args += [f"--bearer-token={params.bearer_token}"]
        if getattr(params, "auth_user", None):
            args += [f"--auth-user={params.auth_user}"]
        if getattr(params, "auth_pass", None):
            args += [f"--auth-pass={params.auth_pass}"]

    if params.replace:
        args.append("--replace")

    diff_with: str | None = params.diff_with
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
    diff_with: str | None = params.diff_with
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


def _read_package_password_parameters(
    args: Any,
) -> PkgPasswords:
    pwds = PkgPasswords()

    # collect environment variables
    def collect_pass(
        passwords: list[str],
        env_var_name: str,
        arg_name: str,
    ) -> None:
        env = os.environ.get(env_var_name)
        if env is not None and len(env) > 0:
            passwords.append(env)
        arg = getattr(args, arg_name, [])
        if arg is not None and len(arg) > 0:
            passwords.extend(arg)

    collect_pass(pwds.passwords, "RLSECURE_PACKAGE_PASSWORD", "password")
    collect_pass(pwds.encoded_passwords, "RLSECURE_PACKAGE_ENCODED_LIST", "encoded_password_list")
    collect_pass(pwds.password_lists, "RLSECURE_PACKAGE_PASSWORD_LIST", "password_list")

    return pwds


def _do_init_scan_report_status(  # pylint: disable=R0913
    *,
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    what: str,
    item: str,  # item is a file, a url, a purl or a docker url
    vault_key: str | None = None,
) -> int:
    # VERIFY INSTALL OK
    _install_and_init_rlsecure(
        params,
        reporter,
        vault_key,
    )

    # SCAN
    with reporter.progress_block("Scanning software package"):
        reporter.info(f"Package path: {item}")

        _scan_item(
            what=what,
            item=item,
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
            return 1

    return 0


# PUBLIC


def collect_password_info(
    params: argparse.Namespace,
) -> tuple[PkgPasswords, str | None]:

    # collect password information
    passwords = _read_package_password_parameters(params)
    vault_key = None

    # if internal store is used,
    # we can not use fixed vault password since store is temporary
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
    stream: str | None = None,
) -> None:
    args: list[str] = [
        "rl-deploy",
        "install",
        INSTALL_LOCATION,
        "--no-tracking",
    ]
    if os.path.isfile(CACHE_LOCATION):
        args.append(f"--from-cache={CACHE_LOCATION}")

    args += __collect_install_env_args()
    if stream is not None:
        args.append(f"--stream={stream}")

    __run(args, check=True)


def prune(
    *,
    purl: str,
    before_date: str | None,
    after_date: str | None,
    days_older: int | None,
    hours_older: int | None,
) -> None:
    # vault key not mentioned in documentation: https://docs.secure.software/cli/commands/prune
    store = get_store()

    cmd: list[str] = [
        __executable("rl-secure"),
        "prune",
        "--silent",
        f"--rl-store={store}",
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
    *,
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: str | None = None,
) -> int:
    return _do_init_scan_report_status(
        params=params,
        reporter=reporter,
        passwords=passwords,
        what="file",
        item=params.package_path,
        vault_key=vault_key,
    )


def do_init_scanurl_report_status(
    *,
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: str | None = None,
) -> int:
    return _do_init_scan_report_status(
        params=params,
        reporter=reporter,
        passwords=passwords,
        what="url",
        item=params.import_url,
        vault_key=vault_key,
    )


def do_init_scanpurl_report_status(
    *,
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: str | None = None,
) -> int:
    return _do_init_scan_report_status(
        params=params,
        reporter=reporter,
        passwords=passwords,
        what="purl",
        item=params.import_purl,
        vault_key=vault_key,
    )


def do_init_scandocker_report_status(
    *,
    params: argparse.Namespace,
    reporter: Messages,
    passwords: PkgPasswords,
    vault_key: str | None = None,
) -> int:
    return _do_init_scan_report_status(
        params=params,
        reporter=reporter,
        passwords=passwords,
        what="docker",
        item=params.import_docker,
        vault_key=vault_key,
    )
