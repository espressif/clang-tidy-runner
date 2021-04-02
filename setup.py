import setuptools

setuptools.setup(
    name='pyclang',
    version='0.1.1',
    author='Fu Hanxi',
    author_email='fuhanxi@espressif.com',
    description='A python clang-tidy runner',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.5',
    entry_points={'console_scripts': [
        'idf_clang = pyclang.scripts.idf_clang:main'
    ]}
)
