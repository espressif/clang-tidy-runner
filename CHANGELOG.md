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
