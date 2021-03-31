import setuptools

setuptools.setup(
    name='pyclang',
    version='0.0.1',
    author='Fu Hanxi',
    author_email='fuhanxi@espressif.com',
    description='A python clang-tidy runner',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
