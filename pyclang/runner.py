import json
import os
import re
import subprocess
import sys
from datetime import datetime
from functools import wraps
from typing import Any

import yaml


def _remove_prefix(s, prefix):  # type: (str, str) -> str
    while s.startswith(prefix):
        s = s[len(prefix):]
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

    # clang-tidy warnings format:      FILE_PATH:LINENO:COL :MSG   [ERROR IDENTIFIER]
    CLANG_TIDY_REGEX = re.compile(r'([\w/.\- ]+):(\d+):(\d+): (.+) \[([\w\-,.]+)]')

    def __init__(self, dirs, cores=os.cpu_count(), **kwargs):
        self.dirs = dirs

        # TODO: multi-process support. currently the closure function in ``chain`` can't be serialized by pickle,
        #   so we can't use ProcessPoolExecutor
        self.cores = len(dirs) if len(dirs) < cores else cores

        # general arguments
        self.build_dir = kwargs.pop('build_dir', 'build')
        self.output_path = kwargs.pop('output_path', None)
        if self.output_path:
            os.makedirs(self.output_path, exist_ok=True)
        self.log_path = kwargs.pop('log_path', None)

        # idf related
        self.compile_commands_fn = 'compile_commands.json'
        self.limit_file = kwargs.pop('limit_file', None)
        if self.limit_file and os.path.isfile(self.limit_file):
            with open(self.limit_file) as fr:
                self.limit_file_json = yaml.load(fr, Loader=yaml.FullLoader)
        else:
            self.limit_file_json = None

        if self.limit_file_json:
            self.ignore_files = self.limit_file_json.get('skip')
            self.ignore_checks = self.limit_file_json.get('ignore')
            self.checks_limitations = self.limit_file_json.get('limits')

        self.xtensa_include_dir = kwargs.pop('xtensa_include_dirs', None)

        # run_clang_tidy related
        self.warn_fn = 'warnings.txt'
        self.run_clang_tidy_py = kwargs.pop('run_clang_tidy_py', 'run-clang-tidy.py')
        self.clang_tidy_check_files = kwargs.pop('file_pattern', '.*')
        self.extra_args = kwargs.pop('extra_args', r'-header-filter=".*\..*" '
                                                   r'-checks="-*,clang-analyzer-core.NullDereference,'
                                                   r'clang-analyzer-unix.*,bugprone-*,-bugprone-macro-parentheses,'
                                                   r'readability-*,performance-*,-readability-magic-numbers,'
                                                   r'-readability-avoid-const-params-in-decls"')

        # normalize related
        self.base_dir = kwargs.pop('base_dir', os.getenv('IDF_PATH', os.getcwd()))

        # assign the rest arguments
        for k, v in kwargs.items():
            setattr(self, str(k), v)

        self._call_chain = []

    def _run(self, folder, log_fs):
        for func in self._call_chain:
            func(folder, log_fs)

    def __call__(self):
        for d in self.dirs:
            if self.log_path:
                fw = open(os.path.join(self.log_path, '{}_{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H:%M:%S'),
                                                                         os.path.basename(d))), 'w')
            else:
                fw = sys.stdout

            self._run(d, fw)

    @staticmethod
    def run_cmd(cmd, stream=sys.stdout, **kwargs):  # type: (str, Any, ...) -> None
        print(cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs)
        for line in p.stdout:
            if not isinstance(line, str):
                line = line.decode()
            stream.write(line)
        p.stdout.close()
        return_code = p.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, cmd)

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

        self.run_cmd(f'idf.py -B {self.build_dir} reconfigure', stream=log_fs, cwd=folder)

    @chain
    def filter_cmd(self, *args):
        folder = args[0]
        log_fs = args[1]

        log_fs.write('****** Filter files and dirs\n')
        log_fs.write('Skipped items:\n')
        for i in self.ignore_files:
            log_fs.write(f'- > {i}\n')

        files = ['*']
        out = []
        compiled_command_fp = os.path.join(folder, self.build_dir, self.compile_commands_fn)
        with open(compiled_command_fp) as fr:
            commands = json.load(fr)
        log_fs.write('Files to be analysed:\n')
        for command in commands:
            # Update compiler flags (add include dirs/remove specific flags)
            cmdline = command['command']
            if self.xtensa_include_dir:
                cmdline = cmdline.replace(' -c ', f' -D__XTENSA__ -isystem{self.xtensa_include_dir} -c ', 1)
            cmdline = cmdline.replace('-fstrict-volatile-bitfields', '')
            cmdline = cmdline.replace('-fno-tree-switch-conversion', '')
            cmdline = cmdline.replace('-fno-test-coverage', '')
            cmdline = cmdline.replace('-mlongcalls', '')
            cmdline = re.sub(r'-fmacro-prefix-map=[^\s]+', '', cmdline)
            command['command'] = cmdline

            for file in files:
                # skip all listed items in limitfile and all assembly files too
                if any(i in command['file'] for i in self.ignore_files) or command['file'].endswith('.S'):
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

        output_path = self.output_path or folder
        warn_file = os.path.join(output_path, f'{os.path.basename(folder)}_{self.warn_fn}')

        with open(warn_file, 'w') as fw:
            # clang-tidy would return 1 when found issue, ignore this return code
            self.run_cmd(f'{self.run_clang_tidy_py} {self.clang_tidy_check_files} {self.extra_args} || true',
                         stream=fw,
                         cwd=os.path.join(folder, self.build_dir))

        with open(warn_file) as fr:
            first_line = fr.readline()
            if 'Enabled checks' not in first_line:
                raise ValueError(first_line)

        log_fs.write(f'clang-tidy report generated: {warn_file}\n')

    @chain
    def check_limits(self, *args):
        folder = args[0]
        log_fs = args[1]

        # if there's no limit in limit file, skip this process
        if not self.checks_limitations:
            return

        output_path = self.output_path or folder
        warn_file = os.path.join(output_path, f'{os.path.basename(folder)}_{self.warn_fn}')
        if os.path.isfile(warn_file):
            with open(warn_file) as fr:
                warnings_str = fr.read()
        else:
            raise FileNotFoundError('warnings file not found')

        res = {check: [] for check in self.checks_limitations.keys()}
        for path, line, col, msg, code in self.CLANG_TIDY_REGEX.findall(warnings_str):
            if code not in res:  # error identifier not in limit field
                continue

            if any(i in path for i in self.ignore_files):  # path in ignore list
                continue

            res[code].append(f'{path}:{line}:{col}: {msg}')

        passed = True
        for code, messages in res.items():
            strikes = len(messages) if messages else 0
            if strikes > self.checks_limitations[code]:
                log_fs.write(f'{code}: Exceed limit: ({strikes} > {self.checks_limitations[code]})\n')
                passed = False
            else:
                log_fs.write(f'{code}: Within limit: ({strikes} <= {self.checks_limitations[code]})\n')

            for message in messages:
                log_fs.write(f'\t{message}\n')

        if not passed:
            sys.exit(1)

    @chain
    def normalize(self, *args):
        """
        Normalize and replace all the paths to relative path in the file with specified base_dir
        """
        folder = args[0]
        log_fs = args[1]

        output_path = self.output_path or folder
        warn_file = os.path.join(output_path, f'{os.path.basename(folder)}_{self.warn_fn}')

        warnings = open(warn_file).readlines()
        with open(warn_file, 'w') as fw:
            for line in warnings:
                result = self.CLANG_TIDY_REGEX.match(line)
                if result:
                    path = result.group(1)
                    norm_path = os.path.relpath(_remove_prefix(os.path.normpath(path), '../'), self.base_dir)
                    # if still have ../, then it's a system file, should not in idf path
                    if '../' in norm_path:
                        norm_path = '/' + _remove_prefix(norm_path, '../')
                    else:
                        norm_path = norm_path
                    line = line.replace(path, norm_path)
                fw.write(line)
        log_fs.write(f'Normalized file {warn_file}\n')
