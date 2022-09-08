import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TextIO, Optional, AnyStr


def to_path(*args: str) -> Path:
    return Path(os.path.join(*args)).resolve()


def to_str(bytes_str: AnyStr) -> str:
    if isinstance(bytes_str, bytes):
        return bytes_str.decode('utf-8', errors='ignore')
    return bytes_str


class KnownIssue(Exception):
    """KnownIssue"""


def run_cmd(
    cmd: str,
    log_stream: TextIO = sys.stdout,
    stream: TextIO = sys.stdout,
    ignore_error: Optional[str] = None,
    **kwargs,
) -> Optional[KnownIssue]:
    log_stream.write('run command: ' + cmd + '\n')
    with tempfile.NamedTemporaryFile() as fw:
        # set stdout and stderr both to subprocess.PIPE may cause deadlock
        # https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait
        p = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=fw, **kwargs
        )
        for line in p.stdout:
            line = to_str(line)
            stream.write(line)
            if stream != sys.stdout:
                sys.stdout.write(line)
        p.stdout.close()

        return_code = p.wait()
        if return_code:
            raw_stderr = to_str(fw.read())
            if ignore_error and ignore_error in raw_stderr:
                return KnownIssue()  # nothing happens
            if raw_stderr:
                sys.stdout.write(
                    f'While running "{cmd}", process returned {return_code} with the following stderr:\n'
                )
                sys.stdout.write(raw_stderr)
                sys.stdout.flush()
                sys.exit(return_code)
