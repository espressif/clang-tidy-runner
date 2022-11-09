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
    license='MIT',
    description='A python clang-tidy runner',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    extras_require={
        'html': ['codereport~=0.2.5', 'pygments<2.12'],
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'console_scripts': ['idf_clang_tidy = pyclang.scripts.idf_clang_tidy:main'],
    },
)
