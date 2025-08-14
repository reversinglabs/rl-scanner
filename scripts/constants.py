import os
from typing import (
    Dict,
    List,
    Optional,
)

REPORT_FORMATS: Dict[str, str] = {  # https://docs.secure.software/api-reference/#tag/Version/operation/getVersionReport
    "cyclonedx": "report.cyclonedx.json",
    "sarif": "report.sarif.json",
    "spdx": "report.spdx.json",
    "rl-checks": "report.checks.json",
    "rl-cve": "report.cve.csv",
    "rl-json": "report.rl.json",
    "rl-summary-pdf": "report.summary.pdf",
    "rl-uri": "report.uri.csv",
}

# not all report types are supported in pack/rl-safe
RL_SAFE_FORMAT_LIST: List[str] = [
    "cyclonedx",
    "sarif",
    "spdx",
    "rl-cve",
    "rl-uri",
    "all",
]

_DEV: bool = os.getenv("ENVIRONMENT", "") == "DEVELOPMENT"

SCANNER_COMMANDS: List[str] = [
    "rl-prune",
    "rl-scan",
    "rl-scan-url",
    "rl-scan-purl",
    # "rl-scan-docker",
]

VALID_PURL_TYPES: List[str] = [
    "pkg:npm/",
    "pkg:pypi/",
    "pkg:gem/",
    "pkg:nuget/",
    "pkg:vsx/",
]

TMP_DIR: str = "/tmp"

CACHE_LOCATION: str = f"{TMP_DIR}/rl-secure.cache"
INSTALL_LOCATION: str = f"{TMP_DIR}/__rlsecure"
RLREPORT_LOCATION: str = f"{TMP_DIR}/__rlsecure-report"
RLSTORE: str = f"{TMP_DIR}/__rlstore"

VAULT_KEY: Optional[str] = None

EXIT_FATAL: int = 101
