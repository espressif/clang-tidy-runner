import argparse

from pyclang import Runner
from pyclang.cli_ext import (common_args, filter_cmd_args, normalize_args,
                             run_clang_tidy_args)


def main():
    parser = argparse.ArgumentParser(parents=[common_args, filter_cmd_args, run_clang_tidy_args, normalize_args],
                                     description='IDF run-clang-tidy wrapper')
    args = parser.parse_args()

    runner = Runner(**vars(args))
    runner.idf_reconfigure().filter_cmd().run_clang_tidy().normalize()
    runner()


if __name__ == '__main__':
    main()
