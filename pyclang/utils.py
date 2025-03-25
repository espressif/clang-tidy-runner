import os
import shlex
import subprocess
import sys
from pathlib import Path

import typing as t


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
    log_stream: t.TextIO = sys.stdout,
    stream: t.TextIO = sys.stdout,
    ignore_error: t.Optional[str] = None,
    expect_returncode: t.Optional[t.Union[t.List[int], int]] = None,
    **kwargs,
) -> t.Optional[KnownIssue]:
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    cmd_str = ' '.join(cmd)

    log_stream.write(f'Running command: "{cmd_str}"...\n')
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
        sys.stderr.write(f'\nERROR: Command "{cmd_str}" failed with exit code {returncode}\n')
        if raw_stderr:
            sys.stderr.write(f'Details:\n{raw_stderr}\n')
        sys.stderr.flush()
        raise SystemExit(returncode)

    if raw_stderr:
        if ignore_error and ignore_error in raw_stderr:
            return KnownIssue()  # nothing happens

        sys.stderr.write(
            f'command "{cmd_str}" gives the following warnings with exitcode {returncode}:\n{raw_stderr}\n'
        )

    return returncode


class FileNotFoundSystemExit(SystemExit):
    """System Exit for FileNotFoundError"""
