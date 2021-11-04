import json
import os
import re
import subprocess
import sys
from datetime import datetime
from functools import wraps
from io import BytesIO
from typing import List, Dict, Optional


def _remove_prefix(s, prefix):  # type: (str, str) -> str
    while s.startswith(prefix):
        s = s[len(prefix) :]
    return s


class Runner:
    """
    Should be used with:
    >> runner = Runner(...args, ...kwargs)
    >> runner = runner.idf_configure().run_clang_tidy().normalize()
    >> runner()

    could use ``@chain`` to add custom method, default arguments are (folder, log_fs), no need to pass manually.
    all related other params should be passed by ``__init__`` function to the Runner itself
    """

    # clang-tidy warnings format:      FILE_PATH:LINENO:COL: SEVERITY: MSG [ERROR IDENTIFIER]
    CLANG_TIDY_REGEX = re.compile(
        r'([\w/.\- ]+):(\d+):(\d+): (.+): (.+) \[([\w\-,.]+)]'
    )
    WARN_FILENAME = 'warnings.txt'
    COMPILE_COMMANDS_FILENAME = 'compile_commands.json'

    def __init__(
        self,
        dirs: List[str],
        cores: int = os.cpu_count(),
        # general arguments
        build_dir: str = 'build',
        output_path: Optional[str] = None,
        log_path: Optional[str] = None,
        # filter arguments
        exclude: Optional[List[str]] = None,
        ignore_clang_checks: Optional[List[str]] = None,
        checks_limitations: Optional[Dict[str, int]] = None,
        xtensa_include_dirs: Optional[str] = None,
        # run_clang_tidy related
        run_clang_tidy_py: str = 'run-clang-tidy.py',
        check_files_regex: str = '.*',
        clang_extra_args: str = (
            r'-header-filter=".*\..*" '
            r'-checks="-*,clang-analyzer-core.NullDereference,clang-analyzer-unix.*,bugprone-*,'
            r'-bugprone-macro-parentheses,readability-*,performance-*,-readability-magic-numbers,'
            r'-readability-avoid-const-params-in-decls"'
        ),
        # normalize arguments
        base_dir: str = os.getenv('IDF_PATH', os.getcwd()),
        **kwargs,
    ):
        self.dirs = dirs

        # TODO: multi-process support. currently the closure function in ``chain`` can't be serialized by pickle,
        #   so we can't use ProcessPoolExecutor
        self.cores = len(dirs) if len(dirs) < cores else cores

        # general arguments
        self.build_dir = build_dir
        self.output_path = output_path
        self.log_path = log_path

        # filter arguments
        self.exclude = exclude
        self.ignore_clang_checks = ignore_clang_checks
        self.checks_limitations = checks_limitations

        self.xtensa_include_dir = xtensa_include_dirs

        # run_clang_tidy arguments
        self.run_clang_tidy_py = run_clang_tidy_py
        self.check_files_regex = check_files_regex
        self.clang_extra_args = clang_extra_args

        # normalize arguments
        self.base_dir = base_dir

        # assign the rest arguments
        for k, v in kwargs.items():
            setattr(self, str(k), v)

        self._call_chain = []

    def _run(self, folder, log_fs, output_dir):
        for func in self._call_chain:
            func(folder, log_fs, output_dir)

    def __call__(self):
        """
        Will auto pass the following arguments to all functions with `@chain` decorated.
        - folder: folder that need to run clang-tidy check
        - log_fs: log file stream, would use sys.stdout when no `log_path` specified
        - output_dir: output folder
        """
        for folder in self.dirs:
            if self.log_path:
                log_fs = open(
                    os.path.join(
                        self.log_path,
                        '{}_{}.log'.format(
                            datetime.now().strftime('%Y-%m-%d_%H:%M:%S'),
                            os.path.basename(folder),
                        ),
                    ),
                    'w',
                )
            else:
                log_fs = sys.stdout

            if self.output_path:
                output_dir = os.path.join(self.output_path, os.path.basename(folder))
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_dir = folder
            self._run(folder, log_fs, output_dir)

    @staticmethod
    def run_cmd(
        cmd, log_stream=sys.stdout, stream=sys.stdout, **kwargs
    ):  # type: (str, BytesIO, BytesIO, ...) -> None
        log_stream.write(cmd + '\n')
        p = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
        for line in p.stdout:
            if not isinstance(line, str):
                line = line.decode()
            stream.write(line)
        p.stdout.close()
        return_code = p.wait()
        if return_code:
            sys.exit(return_code)

    def chain(func):
        """
        Use this wrapper to wrap functions into call chains.

        Restrictions:
            All the wrapped functions should only take argument ``folder``, return ``self``.
            ``folder`` must be optional to fool the interpreter and passed through this decorator
        """

        @wraps(func)
        def wrapper(self):
            def _f(*args, **kwargs):
                return func(self, *args, **kwargs)

            self._call_chain.append(_f)
            return self

        return wrapper

    @chain
    def idf_reconfigure(self, *args):
        """
        Run "idf.py reconfigure" to get the compiled commands
        """
        folder = args[0]
        log_fs = args[1]

        self.run_cmd(
            f'idf.py -B {self.build_dir} reconfigure', log_stream=log_fs, cwd=folder
        )

    @chain
    def filter_cmd(self, *args):
        folder = args[0]
        log_fs = args[1]

        log_fs.write('****** Filter files and dirs\n')
        log_fs.write('Skipped items:\n')
        if self.exclude:
            for i in self.exclude:
                log_fs.write(f'- > {i}\n')

        files = ['*']
        out = []
        compiled_command_fp = os.path.join(
            folder, self.build_dir, self.COMPILE_COMMANDS_FILENAME
        )
        with open(compiled_command_fp) as fr:
            commands = json.load(fr)
        log_fs.write('Files to be analysed:\n')
        for command in commands:
            # Update compiler flags (add include dirs/remove specific flags)
            cmdline = command['command']
            if self.xtensa_include_dir:
                cmdline = cmdline.replace(
                    ' -c ', f' -D__XTENSA__ -isystem{self.xtensa_include_dir} -c ', 1
                )
            cmdline = cmdline.replace('-fstrict-volatile-bitfields', '')
            cmdline = cmdline.replace('-fno-tree-switch-conversion', '')
            cmdline = cmdline.replace('-fno-test-coverage', '')
            cmdline = cmdline.replace('-mlongcalls', '')
            cmdline = re.sub(r'-fmacro-prefix-map=[^\s]+', '', cmdline)
            command['command'] = cmdline

            for file in files:
                # skip all listed items in limitfile and all assembly files too
                if (
                    self.exclude and any(i in command['file'] for i in self.exclude)
                ) or command['file'].endswith('.S'):
                    continue
                if (file in command['file'] and file != '') or file == '*':
                    out.append(command)
                    log_fs.write(f"+ > {command['file']}\n")

        with open(compiled_command_fp, 'w') as fw:
            json.dump(out, fw)
        log_fs.write('******\n')

    @chain
    def run_clang_tidy(self, *args):
        folder = args[0]
        log_fs = args[1]
        output_dir = args[2]

        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        with open(warn_file, 'w') as fw:
            # clang-tidy would return 1 when found issue, ignore this return code
            self.run_cmd(
                f'{self.run_clang_tidy_py} {self.check_files_regex} {self.clang_extra_args} || true',
                log_stream=log_fs,
                stream=fw,
                cwd=os.path.join(folder, self.build_dir),
            )

        with open(warn_file) as fr:
            first_line = fr.readline()
            if 'Enabled checks' not in first_line:
                raise ValueError(first_line)

        log_fs.write(f'clang-tidy report generated: {warn_file}\n')

    @chain
    def check_limits(self, *args):
        log_fs = args[1]
        output_dir = args[2]

        # if there's no limit in limit file, skip this process
        if not self.checks_limitations:
            return

        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        with open(warn_file) as fr:
            warnings_str = fr.read()
        res = {check: [] for check in self.checks_limitations.keys()}
        for path, line, col, severity, msg, code in self.CLANG_TIDY_REGEX.findall(
            warnings_str
        ):
            if code not in res:  # error identifier not in limit field
                continue

            if any(i in path for i in self.exclude):  # path in ignore list
                continue

            res[code].append(f'{path}:{line}:{col}: {severity}: {msg}')

        passed = True
        for code, messages in res.items():
            strikes = len(messages) if messages else 0
            if strikes > self.checks_limitations[code]:
                log_fs.write(
                    f'{code}: Exceed limit: ({strikes} > {self.checks_limitations[code]})\n'
                )
                passed = False
            else:
                log_fs.write(
                    f'{code}: Within limit: ({strikes} <= {self.checks_limitations[code]})\n'
                )

            for message in messages:
                log_fs.write(f'\t{message}\n')

        if not passed:
            sys.exit(1)

    @chain
    def make_html_report(self, *args):
        log_fs = args[1]
        output_dir = args[2]

        try:
            from codereport import ReportItem
        except ImportError:
            log_fs.write(
                'Please run `pip install codereport` to install this optional dependency for this feature'
            )
            sys.exit(1)

        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        with open(warn_file) as fr:
            warnings_str = fr.read()

        res = []
        for path, line, col, severity, msg, code in self.CLANG_TIDY_REGEX.findall(
            warnings_str
        ):
            if self.ignore_clang_checks and any(
                i for i in self.ignore_clang_checks if code in i
            ):
                continue

            if self.exclude and any(i in path for i in self.exclude):
                continue

            res.append(ReportItem(path, line, severity, msg, code, col).dict())

        report_json_fn = os.path.join(output_dir, 'report.json')
        with open(report_json_fn, 'w') as fw:
            json.dump(res, fw, indent=2)

        self.run_cmd(
            f'codereport {report_json_fn} html_report',
            log_stream=log_fs,
            cwd=output_dir,
        )
        log_fs.write(
            f'Please open {output_dir}/html_report/index.html to view the report\n'
        )

    @chain
    def normalize(self, *args):
        """
        Normalize and replace all the paths to relative path in the file with specified base_dir
        """
        log_fs = args[1]
        output_dir = args[2]

        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        with open(warn_file, 'r') as fr:
            warnings = fr.readlines()

        with open(warn_file, 'w') as fw:
            for line in warnings:
                result = self.CLANG_TIDY_REGEX.match(line)
                if result:
                    path = result.group(1)
                    norm_path = os.path.relpath(
                        _remove_prefix(os.path.normpath(path), '../'), self.base_dir
                    )
                    # if still have ../, then it's a system file, should not in idf path
                    if '../' in norm_path:
                        norm_path = '/' + _remove_prefix(norm_path, '../')
                    else:
                        norm_path = norm_path
                    line = line.replace(path, norm_path)
                fw.write(line)
        log_fs.write(f'Normalized file {warn_file}\n')
