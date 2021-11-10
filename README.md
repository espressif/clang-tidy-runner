# Clang Tidy Runner

## Installation

Please install it via `pip install pyclang`.

[![pyclang](https://img.shields.io/pypi/v/pyclang?color=green&label=pyclang)](https://pypi.org/project/pyclang/)

## Examples

```python
import os

from pyclang import Runner

# all the dirs you want to run clang-tidy in, will use this value to pass to all chained methods automatically
runner = Runner([os.path.join(os.environ['IDF_PATH'], 'examples', 'get-started', 'hello_world')])
runner.idf_reconfigure().normalize()  # each function is a step, all these steps are chainable
runner()  # the class instance is callable, call it to run all the chained methods
```

You can write custom chain method by using decorator `@chain`.

Restrictions: all arguments are fixed, you need to pass the rest of them when initializing `Runner` instance with kwargs

- `folder`: which is the folder you passed when initializing `Runner` instance
- `log_fs`: file stream (if you provided `log_path`) or `sys.stdout`

```python
import os

from pyclang import Runner


class CustomRunner(Runner):
    @chain
    def hello(self, *args):
        print('hello world')


# and used by
runner = Runner([os.path.join(os.environ['IDF_PATH'], 'examples', 'get-started', 'hello_world')])
runner.hello().idf_reconfigure()
runner()
```

## CLI Extension

For each custom chain method, you should also define this in `cli_ext.py` if there're additional arguments.

## Use as a script

You can also customize it into a scripts. Now we provide a predefined script: `idf_clang_tidy`, which procedure
is: `idf_reconfigure().filter_cmd().run_clang_tidy().normalize()`. You can run it by `idf_clang_tidy --help` for detail.
