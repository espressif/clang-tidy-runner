import os
import shlex
import subprocess
import sys
from pathlib import Path

import typing as t

from rich.markup import escape
from esp_pylib.logger import log


def to_path(*args: str) -> Path:
    return Path(os.path.expanduser(os.path.join(*args))).resolve()


def to_realpath(filepath: str) -> str:
    return os.path.realpath(os.path.expanduser(filepath))


def to_str(bytes_str: t.AnyStr) -> str:
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


class KnownIssue(Exception):
    """KnownIssue"""


def run_cmd(
    cmd: t.Union[t.List[str], str],
    stream: t.TextIO = sys.stdout,
    ignore_error: t.Optional[str] = None,
    expect_returncode: t.Optional[t.Union[t.List[int], int]] = None,
    **kwargs,
) -> t.Union[KnownIssue, int]:
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    cmd_str = ' '.join(cmd)

    log.print(f'Running command: "{escape(cmd_str)}"...')
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    # live print the stdout as well
    for line in p.stdout:
        line = to_str(line)
        stream.write(line)
        if stream != sys.stdout:
            sys.stdout.write(line)

    if expect_returncode is None:
        expect_returncode = [0]

    if isinstance(expect_returncode, int):
        expect_returncode = [expect_returncode]

    returncode = p.wait()
    raw_stderr = to_str(p.stderr.read())
    if returncode not in expect_returncode:
        log.err(f'Command "{escape(cmd_str)}" failed with exit code {returncode}')
        if raw_stderr:
            log.err(f'Details:\n{escape(raw_stderr)}')
        raise SystemExit(returncode)

    if raw_stderr:
        if ignore_error and ignore_error in raw_stderr:
            return KnownIssue()  # nothing happens

        log.warn(
            f'Command "{escape(cmd_str)}" gives the following warnings with exit code {returncode}:\n{escape(raw_stderr)}'
        )

    return returncode


class FileNotFoundSystemExit(SystemExit):
    """System Exit for FileNotFoundError"""
