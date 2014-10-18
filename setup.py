from setuptools import setup, find_packages
from distutils.core import Extension

ext = Extension(
    "_osx",
    sources=["cider/_osx.m"],
    language="objc",
    extra_link_args=[
        "-Wall",
        "-Werror",
        "-framework", "Foundation",
        "-framework", "AppKit"
    ]
)

setup(
    name='cider',
    author='Michael Sanders',
    author_email='michael [at] msanders [dot] com',
    version='1.0',
    url='https://github.com/msanders/cider',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'rfc3987',
    ],
    entry_points='''
        [console_scripts]
        cider=cider.cli:main
        cyder=cider.cli:main
    ''',
    description='Hassle-free bootstrapping using Homebrew.',
    ext_modules=[ext],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python'
    ],
)
