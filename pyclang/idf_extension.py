import os.path

from pyclang import Runner


def action_extensions(base_actions, project_path):
    def call_runner(subcommand_name, ctx, args, **kwargs):
        useful_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        runner = Runner(
            [args.project_dir],
            build_dir=os.path.basename(args.build_dir),
            **useful_kwargs
        )

        if subcommand_name == 'clang-check':
            runner.idf_reconfigure().run_clang_tidy()
        elif subcommand_name == 'clang-html-report':
            runner.make_html_report()

        runner()

    return {
        'actions': {
            'clang-check': {
                'callback': call_runner,
                'help': 'run clang-tidy check under current folder',
                'options': [
                    {
                        'names': ['--run-clang-tidy-py'],
                        'help': 'run-clang-tidy.py path, this file could be downloaded from llvm. '
                        'will use "run-clang-tidy.py" if not specified.',
                    },
                    {
                        'names': ['--clang-extra-args'],
                        'help': 'run-clang-tidy.py arguments. will use idf default settings if not specified: '
                        r'-header-filter=".*\..*" '
                        r'-checks="-*,clang-analyzer-core.NullDereference,clang-analyzer-unix.*,bugprone-*,'
                        r'-bugprone-macro-parentheses,readability-*,performance-*,-readability-magic-numbers,'
                        r'-readability-avoid-const-params-in-decls"',
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
