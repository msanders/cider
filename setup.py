# -*- coding: utf-8 -*-
from ast import literal_eval
from setuptools import setup, find_packages, Extension
import re

REPO_URL = "https://github.com/msanders/cider"


def module_attr_re(attr):
    return re.compile(r'__{0}__\s*=\s*(.*)'.format(attr))


def grep_attr(body, attr):
    return literal_eval(module_attr_re(attr).search(body).group(1))


def read_description():
    with open("README.md") as f:
        footer = "For more information, see the [GitHub Repository]" \
                 "({0}).".format(REPO_URL)
        filter_re = re.compile(r'.*\b(PyPI|Bitdeli)\b.*')
        contents = filter_re.sub("", f.read()) + "\n" + footer
        return contents.strip()


with open("cider/__init__.py", "r") as f:
    body = f.read()
    version, author = [grep_attr(body, attr) for attr in ("version", "author")]

ext = Extension(
    "cider._osx",
    sources=["cider/_osx.m"],
    language="objc",
    extra_link_args=[
        "-Wall",
        "-Werror",
        "-framework", "Foundation",
        "-framework", "AppKit",
        "-fobjc-arc"
    ]
)

setup(
    name='cider',
    author=author,
    author_email='michael.sanders@fastmail.com',
    version=version,
    url=REPO_URL,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=7.0,<8.0',
        'rfc3987>=1.3.8<2.0.0',
        'PyYAML>=5.1<6.0'
    ],
    entry_points='''
        [console_scripts]
        cider=cider._cli:main
    ''',
    description='Hassle-free bootstrapping using Homebrew.',
    long_description=read_description(),
    long_description_content_type='text/markdown',
    license='MIT',
    ext_modules=[ext],
    platforms=["osx"],
    keywords=["cider", "homebrew", "bootstrap", "automation"],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Objective C',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
        'Topic :: System',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities'
    ],
)
