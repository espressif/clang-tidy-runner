import argparse
import os.path
import sys

try:
    import yaml
except ImportError:
    print('please run "pip install pyyaml" to run idf_clang_tidy')
    sys.exit(1)

from pyclang import Runner
from pyclang.cli_ext import (
    common_args,
    idf_specific_args,
    normalize_args,
    run_clang_tidy_args,
)


def main():
    parser = argparse.ArgumentParser(
        parents=[common_args, idf_specific_args, run_clang_tidy_args, normalize_args],
        description='IDF run-clang-tidy wrapper',
    )
    args = parser.parse_args()

    useful_kwargs = {k: v for k, v in vars(args).items() if v is not None}
    if 'limit_file' in useful_kwargs and os.path.isfile(useful_kwargs['limit_file']):
        with open(useful_kwargs['limit_file']) as fr:
            limit_file_dict = yaml.load(fr, Loader=yaml.FullLoader)
        useful_kwargs['exclude_paths'] = limit_file_dict.get('skip')
        useful_kwargs['ignore_clang_checks'] = limit_file_dict.get('ignore')
        useful_kwargs['checks_limitations'] = limit_file_dict.get('limits')

    runner = Runner(**useful_kwargs)
    runner.idf_reconfigure().remove_command_flags().filter_cmd().run_clang_tidy().check_limits().remove_color_output().normalize()
    runner()


if __name__ == '__main__':
    main()
