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
