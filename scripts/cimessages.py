from contextlib import contextmanager
from typing import (
    List,
    Dict,
    Any,
)


class Messages:  # pylint: disable=too-few-public-methods
    @classmethod
    def create(cls, name: str) -> Any:
        if name == "teamcity":
            return TeamCityMesages()
        return TextMessages()

    # Public Abstract
    @contextmanager
    def progress_block(self, msg: str) -> Any:
        raise RuntimeError("Abstract: must be defined in subclass")

    def info(self, msg: str) -> None:
        raise RuntimeError("Abstract: must be defined in subclass")

    def scan_result(self, passed: bool, msg: str) -> bool:
        raise RuntimeError("Abstract: must be defined in subclass")


class TextMessages(Messages):
    def _block_start(self, msg: str) -> None:
        print(f"Started: {msg}", flush=True)

    def _block_end(self, msg: str) -> None:
        print(f"Finished: {msg}", flush=True)

    # Public
    def info(self, msg: str) -> None:
        print(f"Info: {msg}", flush=True)

    def scan_result(self, passed: bool, msg: str) -> bool:
        if passed:
            print("Scan result: PASS", flush=True)
        else:
            print(f"Scan result: {msg}... FAIL", flush=True)
        return True

    @contextmanager
    def progress_block(self, msg: str) -> Any:
        self._block_start(msg)
        yield
        self._block_end(msg)


class TeamCityMesages(Messages):
    @classmethod
    def _service_message(cls, name: str, msg: Any) -> str:
        def _escape(msg: str) -> str:
            escape_map: Dict[str, str] = {"'": "|'", "|": "||", "\n": "|n", "\r": "|r", "[": "|[", "]": "|]"}
            return "".join(escape_map.get(x, x) for x in msg)

        if isinstance(msg, dict):
            msg_content: List[str] = [f"{k}='{_escape(v)}'" for k, v in msg.items()]
            return f"##teamcity[{name} {' '.join(msg_content)}]"
        return f"##teamcity[{name} '{_escape(msg)}']"

    def _block_start(self, msg: str) -> None:
        print(TeamCityMesages._service_message("progressStart", msg), flush=True)
        print(TeamCityMesages._service_message("blockOpened", {"name": msg}), flush=True)

    def _block_end(self, msg: str) -> None:
        print(TeamCityMesages._service_message("blockClosed", {"name": msg}), flush=True)
        print(TeamCityMesages._service_message("progressFinish", msg), flush=True)

    def _build_problem(self, msg: str) -> None:
        print(TeamCityMesages._service_message("buildProblem", {"description": msg}), flush=True)

    def _build_status(self, msg: str) -> None:
        print(TeamCityMesages._service_message("buildStatus", {"text": msg}), flush=True)

    # Public
    def info(self, msg: str) -> None:
        print(TeamCityMesages._service_message("message", {"text": msg}), flush=True)

    def scan_result(self, passed: bool, msg: str) -> bool:
        if passed:
            self._build_status("Scan result: PASS")
        else:
            self._build_problem(f"Scan result: {msg}... FAIL")
        return False

    @contextmanager
    def progress_block(self, msg: str) -> Any:
        self._block_start(msg)
        yield
        self._block_end(msg)
