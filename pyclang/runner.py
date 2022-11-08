import json
import os
import re
import shutil
import sys
from datetime import datetime
from functools import wraps
from typing import List, Dict, Optional, TextIO

from .utils import to_path, run_cmd


def _remove_prefix(s: str, prefix: str) -> str:
    while s.startswith(prefix):
        s = s[len(prefix) :]
    return s


class KnownIssue(Exception):
    """KnownIssue"""


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

    ANSI_ESCAPE_REGEX = re.compile(
        r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''',
        re.VERBOSE,
    )

    GCC_FLAGS_MAPPING = {
        '-fstrict-volatile-bitfields': '',
        '-fno-tree-switch-conversion': '',
        '-fno-test-coverage': '',
        '-mlongcalls': '-mlong-calls',
    }

    PREFIX_MAP_MAPPING = {
        re.compile(r'-fmacro-prefix-map=[^\s]+'): '',
        re.compile(r'-fdebug-prefix-map=[^\s]+'): '',
        re.compile(r'-ffile-prefix-map=[^\s]+'): '',
    }

    def __init__(
        self,
        dirs: List[str],
        cores: int = os.cpu_count(),
        # general arguments
        build_dir: str = 'build',
        output_path: Optional[str] = None,
        log_path: Optional[str] = None,
        # filter arguments
        all_files: bool = True,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        ignore_clang_checks: Optional[List[str]] = None,
        checks_limitations: Optional[Dict[str, int]] = None,
        xtensa_include_dirs: Optional[str] = None,
        # run_clang_tidy related
        run_clang_tidy_py: str = 'run-clang-tidy.py',
        check_files_regex: Optional[List[str]] = None,
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
        self.all_files = all_files
        self.include_paths = (
            [to_path(p) for p in include_paths] if include_paths else []
        )
        self.exclude_paths = (
            [to_path(p) for p in exclude_paths] if exclude_paths else []
        )
        self.ignore_clang_checks = ignore_clang_checks
        self.checks_limitations = checks_limitations

        self.xtensa_include_dir = xtensa_include_dirs

        # run_clang_tidy arguments
        if os.path.isfile(os.path.realpath(run_clang_tidy_py)):
            self.run_clang_tidy_py = os.path.realpath(run_clang_tidy_py)
        else:
            self.run_clang_tidy_py = run_clang_tidy_py
        self.check_files_regex = check_files_regex if check_files_regex else ['.*']
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

    def get_check_warn_file(self, log_fs: TextIO, output_dir: str) -> str:
        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        if not os.path.isfile(warn_file):
            log_fs.write(
                f'{warn_file} not found. Please run clang-tidy to generate this file\n'
            )
            sys.exit(1)

        return warn_file

    @chain
    def idf_reconfigure(self, *args) -> 'Runner':
        """
        Run "idf.py reconfigure" to get the compiled commands
        """
        folder = args[0]
        log_fs = args[1]

        # tell IDF build system to prepare compilation commands for Clang based toolchain
        env = os.environ.copy()
        env['IDF_TOOLCHAIN'] = 'clang'

        run_cmd(
            f'idf.py -B {self.build_dir} reconfigure', log_stream=log_fs, cwd=folder, env=env
        )

    @chain
    def remove_command_flags(self, *args):
        folder = args[0]

        # see if the IDF version recognizes Clang toolchain
        with open(os.path.join(folder, self.build_dir, 'CMakeCache.txt'), 'r') as cmake_cache_fp:
            cmake_cache = cmake_cache_fp.read()
        if 'IDF_TOOLCHAIN:STRING=clang' in cmake_cache:
            # it does! nothing to do here, compile_commands.json already contains clang-compatible flags
            return

        # if it doesn't, need to remove GCC-specific flags from compile_commands.json
        compiled_command_fp = os.path.join(
            folder, self.build_dir, self.COMPILE_COMMANDS_FILENAME
        )
        with open(compiled_command_fp) as fr:
            file_str = fr.read()
            for k, v in self.GCC_FLAGS_MAPPING.items():
                file_str = file_str.replace(f' {k} ', ' ' if not v else f' {v} ')

            for k, v in self.PREFIX_MAP_MAPPING.items():
                file_str = k.sub(v, file_str)

        with open(compiled_command_fp, 'w') as fw:
            fw.write(file_str)

    @chain
    def filter_cmd(self, *args):
        folder = args[0]
        log_fs = args[1]

        log_fs.write('****** Filter files and dirs ******\n')
        if self.all_files:
            log_fs.write('Including all files.\n')
        else:
            if self.include_paths:
                log_fs.write('Included paths:\n')
                for i in self.include_paths:
                    log_fs.write(f'+ > {str(i)}\n')
            if self.exclude_paths:
                log_fs.write('Excluded paths:\n')
                for i in self.exclude_paths:
                    log_fs.write(f'- > {str(i)}\n')

        out = []
        compiled_command_fp = os.path.join(
            folder, self.build_dir, self.COMPILE_COMMANDS_FILENAME
        )
        with open(compiled_command_fp) as fr:
            commands = json.load(fr)

        log_fs.write('Files to be analysed:\n')
        for command in commands:
            _file = to_path(command['file'])
            if _file.suffix == '.S':  # assembly file
                continue

            if to_path(folder, self.build_dir) in _file.parents:  # build dir
                continue

            if not self.all_files:
                # skip files in exclude paths
                if self.exclude_paths and any(
                    i in _file.parents for i in self.exclude_paths
                ):
                    continue
                # skip files not in include paths or project dir
                if not (
                    (
                        self.include_paths
                        and any(i in _file.parents for i in self.include_paths)
                    )
                    or to_path(folder) in _file.parents
                ):
                    continue

            out.append(command)
            log_fs.write(f"+ > {command['file']}\n")

        with open(compiled_command_fp, 'w') as fw:
            json.dump(out, fw)
        log_fs.write(f'{"*" * 35}\n')

    @chain
    def run_clang_tidy(self, *args):
        folder = args[0]
        log_fs = args[1]
        output_dir = args[2]

        warn_file = os.path.join(output_dir, self.WARN_FILENAME)
        with open(warn_file, 'w') as fw:
            # clang-tidy would return 1 when found issue, ignore this return code
            run_cmd(
                f'{sys.executable} {self.run_clang_tidy_py} {" ".join(self.check_files_regex)} {self.clang_extra_args} || true',
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

        warn_file = self.get_check_warn_file(log_fs, output_dir)
        with open(warn_file) as fr:
            warnings_str = fr.read()
        res = {check: [] for check in self.checks_limitations.keys()}
        for path, line, col, severity, msg, code in self.CLANG_TIDY_REGEX.findall(
            warnings_str
        ):
            if code not in res:  # error identifier not in limit field
                continue

            if any(
                i in to_path(path).parents for i in self.exclude_paths
            ):  # path in ignore list
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
    def remove_color_output(self, *args):
        log_fs = args[1]
        output_dir = args[2]

        warn_file = self.get_check_warn_file(log_fs, output_dir)
        with open(warn_file) as fr:
            warnings_str = fr.read()
            warnings_str = self.ANSI_ESCAPE_REGEX.sub('', warnings_str)

        with open(warn_file, 'w') as fw:
            fw.write(warnings_str)

        log_fs.write(f'color outputs in "{warn_file}" are eliminated.\n')

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

        warn_file = self.get_check_warn_file(log_fs, output_dir)
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

            if self.exclude_paths and any(
                i in to_path(path).parents for i in self.exclude_paths
            ):
                continue

            res.append(ReportItem(path, line, severity, msg, code, col).dict())

        report_json_fn = os.path.join(output_dir, 'report.json')
        with open(report_json_fn, 'w') as fw:
            json.dump(res, fw, indent=2)

        html_report_folder = os.path.join(output_dir, 'html_report')
        if os.path.isdir(html_report_folder):
            shutil.rmtree(html_report_folder)

        known_issue = run_cmd(
            f'codereport {report_json_fn} html_report --prefix={self.base_dir}',
            log_stream=log_fs,
            cwd=output_dir,
            ignore_error='AssertionError: No existing files found',
        )
        if known_issue:
            log_fs.write('No issue found\n')
        else:
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
