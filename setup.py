from setuptools import setup, find_packages

setup(
    name='cider',
    author='Michael Sanders',
    version='0.1',
    url='https://github.com/msanders/cider',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'parallel',
    ],
    entry_points='''
        [console_scripts]
        cider=cider.cli:main
        cyder=cider.cli:main
    ''',
    description='Hassle-free bootstrapping using Homebrew.',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python'
    ],
)
