import json
import os
import re
import subprocess
import sys
from datetime import datetime
from functools import wraps

try:
    from typing import Any
except ImportError:
    pass


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

    # clang-tidy warnings format:              FILE_PATH: LINE NO:  COL NO:   LEVEL: MESSAGE
    CLANG_TIDY_REGEX = re.compile(r'(.+|[a-zA-Z]:\\\\.+):([0-9]+):([0-9]+): ([^:]+): (.+)')

    def __init__(self, dirs, cores=os.cpu_count(), **kwargs):
        self.dirs = dirs
        self.cores = len(dirs) if len(dirs) < cores else cores

        # general arguments
        self.build_dir = kwargs.pop('build_dir', 'build')
        self.output_dir = kwargs.pop('output_dir', None)
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
        self.log_dir = kwargs.pop('log_dir', None)

        # filter_cmd related
        self.compile_commands_fn = 'compile_commands.json'
        self.limit_file = kwargs.pop('limit_file', None)
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
        # TODO: multi-process support. currently the closure function in ``chain`` can't be serialized by pickle, so
        #   we can't use ProcessPoolExecutor

        for d in self.dirs:
            if self.log_dir:
                fw = open(os.path.join(self.log_dir,
                                       '{}_{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H:%M:%S'),
                                                          os.path.basename(d))),
                          'w')
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
        :return: None
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

        self.run_cmd('idf.py -B {} reconfigure'.format(self.build_dir), stream=log_fs, cwd=folder)

    @chain
    def filter_cmd(self, *args):
        import yaml

        folder = args[0]
        log_fs = args[1]

        log_fs.write('****** Filter files and dirs\n')
        skip_items = []
        if self.limit_file and os.path.isfile(self.limit_file):
            with open(self.limit_file) as fr:
                limit_file = yaml.load(fr, Loader=yaml.SafeLoader)
            if limit_file['skip']:
                skip_items = limit_file['skip']
        log_fs.write('Skipped items:\n')
        for i in skip_items:
            log_fs.write('- > {}\n'.format(i))

        files = ['*']
        out = []
        compiled_command_fp = os.path.join(folder, self.build_dir, self.compile_commands_fn)
        commands = json.load(open(compiled_command_fp))
        log_fs.write('Files to be analysed:\n')
        for command in commands:
            # Update compiler flags (add include dirs/remove specific flags)
            if self.xtensa_include_dir:
                command['command'] = command['command'].replace(
                    ' -c ', ' -D__XTENSA__ -isystem{} -c '.format(self.xtensa_include_dir), 1)
            command['command'] = command['command'].replace('-fstrict-volatile-bitfields', '')
            command['command'] = command['command'].replace('-fno-tree-switch-conversion', '')
            command['command'] = command['command'].replace('-fno-test-coverage', '')
            command['command'] = command['command'].replace('-mlongcalls', '')
            for file in files:
                # skip all listed items in limitfile and all assembly files too
                if any(i in command['file'] for i in skip_items) or command['file'].endswith('.S'):
                    continue
                if (file in command['file'] and file != '') or file == '*':
                    out.append(command)
                    log_fs.write('+ > {}\n'.format(command['file']))

        with open(compiled_command_fp, 'w') as fw:
            json.dump(out, fw)
        log_fs.write('******\n')

    @chain
    def run_clang_tidy(self, *args):
        folder = args[0]
        log_fs = args[1]

        output_dir = self.output_dir or folder
        warn_file = os.path.join(output_dir, self.warn_fn)

        with open(warn_file, 'w') as fw:
            # clang-tidy would return 1 when found issue, ignore this return code
            self.run_cmd(
                '{} {} {} || true'.format(self.run_clang_tidy_py, self.clang_tidy_check_files, self.extra_args),
                stream=fw, cwd=os.path.join(folder, self.build_dir))
        log_fs.write('clang-tidy report generated: {}\n'.format(warn_file))

    @chain
    def normalize(self, *args):
        """
        Normalize and replace all the paths to relative path in the file with specified base_dir
        :return: None
        """
        folder = args[0]
        log_fs = args[1]

        output_dir = self.output_dir or folder
        f_in = os.path.join(output_dir, self.warn_fn)
        f_out = os.path.join(output_dir, '{}_{}'.format(os.path.basename(folder), self.warn_fn))

        f_in_lines = open(f_in).readlines()
        with open(f_out, 'w') as fw:
            for line in f_in_lines:
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
        log_fs.write('Normalized from {} to {}\n'.format(f_in, f_out))
