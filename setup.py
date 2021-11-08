import codecs
import os
import re

import setuptools


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


def get_version():
    regex = re.compile(r'^version = "([0-9.]+)"$', re.MULTILINE)
    return regex.findall(read('pyproject.toml'))[0]


setuptools.setup(
    name='pyclang',
    version=get_version(),
    author='Fu Hanxi',
    author_email='fuhanxi@espressif.com',
    description='A python clang-tidy runner',
    long_description=read('README.md'),
    packages=setuptools.find_packages(),
    extras_require={
        'make_html_report': ['codereport'],
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': ['idf_clang = pyclang.scripts.idf_clang:main'],
    },
)
