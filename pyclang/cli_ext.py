import argparse
import os

common_args = argparse.ArgumentParser(add_help=False)
common_args.add_argument(
    'dirs',
    nargs='+',
    type=os.path.realpath,
    help='All the directories you want to run clang-tidy in.',
)
common_args.add_argument(
    '--build-dir', help='Project build directory, will use "build" if not specified.'
)
common_args.add_argument(
    '--output-path',
    type=os.path.realpath,
    help='Where the newly generated files locates, will be placed under each "dirs" item if not specified.',
)
common_args.add_argument(
    '--log-path',
    type=os.path.realpath,
    help='Where the log files will be written to, will use stdout if not specified.',
)
common_args.add_argument(
    '--exit-code',
    action='store_true',
    help='Exit with code based on the results of the code analysis. By default, exit code reflects the success of running the tool only.',
)

idf_specific_args = argparse.ArgumentParser(add_help=False)
idf_specific_args.add_argument(
    '--limit-file', help='Definitions of ignore checks and files/directories to skip.'
)
idf_specific_args.add_argument(
    '--xtensa-include-dir',
    nargs='?',
    const='/opt/espressif/xtensa-esp32-elf-clang/xtensa-esp32-elf/include/',
    help='Extra include directory for Xtensa related header files.',
)

run_clang_tidy_args = argparse.ArgumentParser(add_help=False)
run_clang_tidy_args.add_argument(
    '--check-files-regex',
    nargs='*',
    help='Files to be processed (regex on path), will use ".*" to check all files if not specified.',
)
run_clang_tidy_args.add_argument(
    '--run-clang-tidy-py',
    help='run-clang-tidy.py path, this file could be downloaded from llvm, '
    'will use "run-clang-tidy.py" if not specified.',
)
run_clang_tidy_args.add_argument(
    '--clang-extra-args',
    help='run-clang-tidy.py arguments, will use ESP-IDF default settings if not specified: '
    r'-header-filter=".*\..*" '
    '-checks="-*,clang-analyzer-core.NullDereference,clang-analyzer-unix.*,bugprone-*,'
    '-bugprone-macro-parentheses,readability-*,performance-*,-readability-magic-numbers,'
    '-readability-avoid-const-params-in-decls"',
)

normalize_args = argparse.ArgumentParser(add_help=False)
normalize_args.add_argument(
    '--base-dir',
    help='Base directory to translate to relative path, will use IDF_PATH (if set) or current dir if not specified.',
)
