import os.path

try:
    import yaml
except ImportError:
    yaml = None

import rich_click as click
from esp_pylib.cli_options import OptionEatAll
from esp_pylib.errors import FatalError
from esp_pylib.excepthook import install_exception_reporting
from esp_pylib.logger import log
from rich.markup import escape

from pyclang import Runner


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('dirs', nargs=-1, type=click.Path(resolve_path=True))
@click.option(
    '--build-dir',
    default=None,
    help='Project build directory, will use "build" if not specified.',
)
@click.option(
    '--output-path',
    default=None,
    type=click.Path(resolve_path=True),
    help='Where the newly generated files are located, will be placed under each "dirs" item if not specified.',
)
@click.option(
    '--log-path',
    default=None,
    type=click.Path(resolve_path=True),
    help='Where the log files will be written to, will use stdout if not specified.',
)
@click.option(
    '--exit-code',
    is_flag=True,
    default=False,
    help='Exit with code based on the results of the code analysis. '
    'By default, exit code reflects the success of running the tool only.',
)
@click.option(
    '--limit-file',
    default=None,
    help='Definitions of ignore checks and files/directories to skip.',
)
@click.option(
    '--xtensa-include-dir',
    default=None,
    is_flag=False,
    flag_value='/opt/espressif/xtensa-esp32-elf-clang/xtensa-esp32-elf/include/',
    help='Extra include directory for Xtensa related header files. '
    'When passed without a value, defaults to /opt/espressif/xtensa-esp32-elf-clang/xtensa-esp32-elf/include/.',
)
@click.option(
    '--check-files-regex',
    multiple=True,
    cls=OptionEatAll,
    help='Files to be processed (regex on path). '
    'Accepts multiple values in one invocation or via repeated flags. '
    'Will use ".*" to check all files if not specified.',
)
@click.option(
    '--run-clang-tidy-py',
    default=None,
    help='run-clang-tidy.py path, this file could be downloaded from llvm. '
    'Will use "run-clang-tidy.py" if not specified.',
)
@click.option(
    '--clang-extra-args',
    default=None,
    help='run-clang-tidy.py arguments, will use ESP-IDF default settings if not specified: '
    r'-header-filter=".*\..*" '
    '-checks="-*,clang-analyzer-core.NullDereference,clang-analyzer-unix.*,bugprone-*,'
    '-bugprone-macro-parentheses,readability-*,performance-*,-readability-magic-numbers,'
    '-readability-avoid-const-params-in-decls"',
)
@click.option(
    '--base-dir',
    default=None,
    help='Base directory to translate to relative path, '
    'will use IDF_PATH (if set) or current dir if not specified.',
)
def main(
    dirs,
    build_dir,
    output_path,
    log_path,
    exit_code,
    limit_file,
    xtensa_include_dir,
    check_files_regex,
    run_clang_tidy_py,
    clang_extra_args,
    base_dir,
):
    install_exception_reporting()

    if not dirs:
        raise click.UsageError('At least one directory is required.')

    useful_kwargs = {}
    for key, val in {
        'build_dir': build_dir,
        'output_path': output_path,
        'log_path': log_path,
        'xtensa_include_dirs': xtensa_include_dir,
        'run_clang_tidy_py': run_clang_tidy_py,
        'clang_extra_args': clang_extra_args,
        'base_dir': base_dir,
    }.items():
        if val is not None:
            useful_kwargs[key] = val

    if exit_code:
        useful_kwargs['exit_code'] = True

    if check_files_regex:
        useful_kwargs['check_files_regex'] = list(check_files_regex)

    if limit_file and os.path.isfile(limit_file):
        if yaml is None:
            log.die('please run "pip install pyyaml" to use --limit-file')
        with open(limit_file) as fr:
            limit_file_dict = yaml.load(fr, Loader=yaml.FullLoader)
        useful_kwargs['exclude_paths'] = limit_file_dict.get('skip')
        useful_kwargs['ignore_clang_checks'] = limit_file_dict.get('ignore')
        useful_kwargs['checks_limitations'] = limit_file_dict.get('limits')

    try:
        runner = Runner(list(dirs), **useful_kwargs)
        runner.idf_reconfigure().remove_command_flags().filter_cmd().run_clang_tidy().check_limits().remove_color_output().normalize()
        runner()
    except FatalError as e:
        log.die(escape(str(e)))


if __name__ == '__main__':
    main()
