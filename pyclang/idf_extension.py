import os.path
import sys

from pyclang import Runner


def action_extensions(base_actions, project_path):
    def get_toolchain(args):
        cache_path = os.path.join(args.build_dir, 'CMakeCache.txt')
        if not os.path.exists(cache_path):
            return None
        with open(cache_path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('IDF_TOOLCHAIN:STRING='):
                    return line.split('=', maxsplit=1)[1].strip()
        return None

    def check_clang_toolchain(subcommand_name, args):
        toolchain = get_toolchain(args)
        if not toolchain or toolchain == 'clang':
            return
        print((f'WARNING: clang action "{subcommand_name}" is intended for use '
               f'with "IDF_TOOLCHAIN" set to "clang", but the current toolchain is '
               f'set to "{toolchain}".'), file=sys.stderr)

    def call_runner(subcommand_name, ctx, args, **kwargs):
        # idf extension don't need default values
        kwargs['clang_extra_args'] = kwargs.pop('run_clang_tidy_options', None)
        kwargs['check_files_regex'] = kwargs.pop('patterns', None)

        useful_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        runner = Runner(
            [args.project_dir],
            build_dir=os.path.basename(args.build_dir),
            **useful_kwargs
        )

        if subcommand_name == 'clang-check':
            runner.idf_reconfigure().filter_cmd().remove_command_flags().run_clang_tidy().remove_color_output()
        elif subcommand_name == 'clang-html-report':
            runner.make_html_report()

        runner()

        # Display a warning if the extension was launched for a project using a toolchain other than clang.
        check_clang_toolchain(subcommand_name, args)

    return {
        'actions': {
            'clang-check': {
                'callback': call_runner,
                'help': 'run clang-tidy check under current folder, write the output into "warnings.txt"',
                'arguments': [
                    {
                        'names': ['patterns'],
                        'nargs': -1,
                    }
                ],
                'options': [
                    {
                        'names': ['--all-files'],
                        'help': 'Run clang-tidy with all files. Default run with project dir files only. '
                        '"--include-path" and "--exclude-path" would be ignored if using this flag.',
                        'is_flag': True,
                    },
                    {
                        'names': ['--run-clang-tidy-py'],
                        'help': 'run-clang-tidy.py path, this file could be downloaded from llvm. '
                        'will use "run-clang-tidy.py" if not specified.',
                    },
                    {
                        'names': ['--run-clang-tidy-options'],
                        'help': 'all optional arguments would be passed to run-clang-tidy.py. '
                        'the value should be double-quoted',
                    },
                    {
                        'names': ['--include-paths'],
                        'multiple': True,
                        'help': 'include extra files besides of the project dir. '
                        'This option can be used for multiple times.',
                    },
                    {
                        'names': ['--exclude-paths'],
                        'multiple': True,
                        'help': 'exclude extra files besides of the project dir. '
                        'This option can be used for multiple times.',
                    },
                    {
                        'names': ['--exit-code'],
                        'help': 'Exit with code based on the results of the code analysis. '
                        'By default, exit code reflects the success of running the tool only.',
                        'is_flag': True,
                    },
                ],
            },
            'clang-html-report': {
                'callback': call_runner,
                'help': 'generate html report to "html_report" folder by reading "warnings.txt" '
                '(may take a few minutes). '
                'This feature requires extra dependency "codereport". '
                'Please install this by running "pip install codereport"',
            },
        }
    }
