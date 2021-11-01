import os.path

from pyclang import Runner


def action_extensions(base_actions, project_path):
    def call_runner(subcommand_name, ctx, args, **kwargs):
        # idf extension don't use default values
        kwargs['clang_extra_args'] = kwargs.get('run_clang_tidy_options', '') or ''

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
                'help': 'run clang-tidy check under current folder, write the output into "warnings.txt"',
                'options': [
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
