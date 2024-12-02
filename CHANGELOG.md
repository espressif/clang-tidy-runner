## v0.6.0 (2024-12-02)

### New Features

- drop support for ESP-IDF v4.4 and Python 3.6

### Bug Fixes

- Windows - run-clang-tidy.py not found in your PATH
- update codereport version to allow usage of pygments 2.12+

## v0.5.0 (2024-09-02)

### New Features

- add warning for ESP-IDF actions if IDF_TOOLCHAIN is not set to clang

## v0.4.2 (2023-10-16)

### Fix

- **idf_extension**: Don't override the clang_extra_args with empty string if not specified

## v0.4.1 (2023-09-27)

### Fix

- check project files only by default

## v0.4.0 (2023-09-22)

### Feat

- support default value run-clang-tidy as well

### Fix

- skip writing report.json and html reports when there's no issue

## v0.3.0 (2023-07-31)

### Feat

- add support for '--exit-code' flag

### Fix

- call exe file directly

## v0.2.3 (2023-02-17)

### Fix

- use real path when calling idf.py

## v0.2.2 (2022-11-09)

### Fix

- update dependency  for codereport related packages
- run clang-tidy check at the src folder instead of build dir
- stop using `shell=True` for subprocess.Popen
- check if `run-clang-tidy.py` exists while calling, not raise ValueError if not found "Enabled checks"

## v0.2.1 (2022-09-16)

### Fix

- prefix the call to run_clang_tidy.py with python
- don't open temporary file twice

## v0.2.0 (2022-04-14)

### Fix

- add jinja2 version constraint
- fix error when running codereport with empty warnings file
- remove duplicated cli option

### Feat

- remove color output when running clang-check
- rename extras_require to "html"
- duplicate clang-tidy output to sys.stdout and file output
- add cli option "--include-paths" and "--exclude-paths"
- add cli option '--all-related-files', run clang-tidy with project dir only by default

## v0.1.2 (2021-11-15)

### Fix

- add idf_path as prefix in codereport
- remove html report folder if exists
- use realpath for `run_clang_tidy_py` if exists, respect files under $PATH
- add error message when missing pyyaml in idf_clang_tidy
- remove asci color in warnings.txt when generating html report

### Feat

- add cli argument `files` for file paths regex
- extract chain method `remove_color_output`
- rename idf_clang -> idf_clang_tidy
- remove gcc flags

## v0.1.1 (2021-11-08)

### Fix

- remove pyyaml requirement

## v0.1.0 (2021-11-08)

### Feat

- add idf.py extension
- add idf_clang to cli
