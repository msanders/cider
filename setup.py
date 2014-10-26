from ast import literal_eval
from setuptools import setup, find_packages, Extension
import re


def module_attr_re(attr):
    return re.compile(r'__{0}__\s*=\s*(.*)'.format(attr))


def grep_attr(body, attr):
    return str(literal_eval(module_attr_re("version").search(
        body.decode("utf-8")
    ).group(1)))

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
        "-framework", "AppKit"
    ]
)

setup(
    name='cider',
    author=author,
    author_email='michael [at] msanders [dot] com',
    version=version,
    url='https://github.com/msanders/cider',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'rfc3987',
    ],
    entry_points='''
        [console_scripts]
        cider=cider._cli:main
        cyder=cider._cli:main
    ''',
    description='Hassle-free bootstrapping using Homebrew.',
    license='MIT',
    ext_modules=[ext],
    platforms=["osx"],
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
        'Topic :: Software Development',
        'Topic :: System',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities'
    ],
)
