import argparse
import os

common_args = argparse.ArgumentParser(add_help=False)
common_args.add_argument('dirs', nargs='+', type=os.path.realpath,
                         help='all the dirs you want to run clang-tidy in')
common_args.add_argument('--build-dir', default='build',
                         help='build dir')
common_args.add_argument('--output-path', required=False, type=os.path.realpath,
                         help='where the newly generated files locates, will use "dirs" item if not specified')
common_args.add_argument('--log-path', required=False, type=os.path.realpath,
                         help='where the log files will be write to. will use stdout if not specified')

idf_specific_args = argparse.ArgumentParser(add_help=False)
idf_specific_args.add_argument('--limit-file', required=False,
                               help='definitions of ignore checks and files/dirs to skip')
idf_specific_args.add_argument('--xtensa-include-dir', nargs='?',
                               const='/opt/espressif/xtensa-esp32-elf-clang/xtensa-esp32-elf/include/',
                               help='extra include dir for xtensa related header files')

run_clang_tidy_args = argparse.ArgumentParser(add_help=False)
run_clang_tidy_args.add_argument('--run-clang-tidy-py', default='run-clang-tidy.py',
                                 help='run-clang-tidy.py path, download from llvm')
run_clang_tidy_args.add_argument('--file-pattern', default='.*',
                                 help='file pattern, relative to the folder pass into "dirs"')
run_clang_tidy_args.add_argument('--extra-args', default=r'-header-filter=".*\..*" '
                                                         r'-checks="-*,clang-analyzer-core.NullDereference,'
                                                         r'clang-analyzer-unix.*,bugprone-*,'
                                                         r'-bugprone-macro-parentheses,readability-*,performance-*,'
                                                         r'-readability-magic-numbers,'
                                                         r'-readability-avoid-const-params-in-decls"',
                                 help='run-clang-tidy.py arguments')

normalize_args = argparse.ArgumentParser(add_help=False)
normalize_args.add_argument('--base-dir', default=os.getcwd(),
                            help='base dir to translate to relative path')
