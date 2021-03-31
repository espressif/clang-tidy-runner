import setuptools

setuptools.setup(
    name='pyclang',
    version='0.0.2',
    author='Fu Hanxi',
    author_email='fuhanxi@espressif.com',
    description='A python clang-tidy runner',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
