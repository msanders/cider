# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from rfc3987 import parse as urlparse
from shutil import copy2 as cp
from subprocess import CalledProcessError
from tempfile import mkdtemp
import _osx as osx
import _tty as tty
import click
import copy
import errno
import glob
import os
import platform
import pwd
import re
import subprocess
import sys

try:
    import simplejson as json
    import simplejson.scanner.JSONDecodeError
except ImportError:
    import json
    JSONDecodeError = ValueError

CIDER_DIR = os.path.join(os.path.expanduser("~"), ".cider")
SYMLINK_DIR = os.path.join(CIDER_DIR, "symlinks")
BOOTSTRAP_FILE = os.path.join(CIDER_DIR, "bootstrap.json")
DEFAULTS_FILE = os.path.join(CIDER_DIR, "defaults.json")
CACHE_DIR = os.path.join(CIDER_DIR, ".cache")
SYMLINK_TARGETS_FILE = os.path.join(CACHE_DIR, "symlink_targets.json")

_defaults_true_re = re.compile(r"\bY(ES)?\b", re.I)
_defaults_false_re = re.compile(r"\bN(O)?\b", re.I)


class CiderException(Exception):
    def __init__(self, message, exit_code=None):
        if exit_code is None:
            exit_code = 1
        Exception.__init__(self, message)
        self.exit_code = exit_code


class JSONError(CiderException):
    def __init__(self, message, filepath, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.filepath = filepath


class UnsupportedOSError(CiderException):
    def __init__(self, message, macos_version, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.macos_version = macos_version


class XcodeMissingError(CiderException):
    def __init__(self, message, url, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.url = url


class BrewMissingError(CiderException):
    def __init__(self, message, url, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.url = url


class BootstrapMissingError(CiderException):
    def __init__(self, message, path, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.path = path


class SymlinkError(CiderException):
    def __init__(self, message, exit_code=None):
        CiderException.__init__(self, message, exit_code)


def AppMissingError(CiderException):
    def __init__(self, message, exit_code=None):
        CiderException.__init__(self, message, exit_code)


def _spawn(args, **kwargs):
    check_call = kwargs.get("check_call", True)
    check_output = kwargs.get("check_output", False)
    debug = kwargs.get("debug", False)

    custom_params = ["check_call", "check_output", "debug"]
    params = dict((k, v) for (k, v) in kwargs.iteritems()
                  if k not in custom_params)

    tty.putdebug(" ".join(args), debug)

    if check_output:
        return subprocess.check_output(args, **params)
    elif check_call:
        return subprocess.check_call(args, **params)
    else:
        return subprocess.call(args, **params)


def _curl(url, path):
    return _spawn(["curl", url, "-o", path, "--progress-bar"])


def _safe_install(formula, debug=None, cask=None):
    if cask is None:
        cask = False
    try:
        args = ["brew"] + (["cask"] if cask else [])
        args += ["install"] + formula.split(" ")
        args += (["-d"] if debug else [])
        _spawn(args, debug=debug)
    except CalledProcessError as e:
        sys.stdout.write(
            "Failed to install {0}. Continue? [y/N] ".format(formula)
        )
        if sys.stdin.read(1).lower() != "y":
            raise


def _mkdir_p(pathname):
    try:
        os.makedirs(pathname)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(pathname):
            raise


def _touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def _read_json(path, fallback=None):
    try:
        with open(path, "r") as f:
            try:
                contents = json.loads(f.read())
            except JSONDecodeError as e:
                raise JSONError(e, path)
            return contents
    except IOError as e:
        if fallback is not None:
            if e.errno == errno.ENOENT:
                return fallback

        raise


def _modify_json(path, transform):
    with open(path, "r+") as f:
        try:
            contents = json.loads(f.read())
        except JSONDecodeError as e:
            raise JSONError(e, path)

        old_contents = contents
        contents = transform(copy.deepcopy(contents))
        changed = bool(old_contents != contents)

        if changed:
            f.seek(0)
            f.write(json.dumps(
                contents,
                indent=4,
                sort_keys=True,
                separators=(',', ': ')
            ))
            f.truncate()

        return changed


def _write_json(path, contents):
    with open(path, "w") as f:
        f.write(json.dumps(
            contents,
            indent=4,
            sort_keys=True,
            separators=(',', ': ')
        ))


def _read_bootstrap():
    if not os.path.isfile(BOOTSTRAP_FILE):
        raise BootstrapMissingError(
            "Bootstrap file not found. Expected at {0}".format(
                _collapseuser(BOOTSTRAP_FILE)
            ),
            BOOTSTRAP_FILE
        )

    return _read_json(BOOTSTRAP_FILE)


def _modify_bootstrap(key, transform=None):
    if transform is None:
        transform = lambda x: x

    def outer_transform(bootstrap):
        bootstrap[key] = sorted(transform(bootstrap.get(key, [])))
        return bootstrap

    return _modify_json(BOOTSTRAP_FILE, outer_transform)


def _modify_defaults(domain, transform):
    def outer_transform(defaults):
        defaults[domain] = transform(defaults.get(domain, {}))
        return defaults

    return _modify_json(DEFAULTS_FILE, outer_transform)


def _write_default(domain, key, value, force=None, debug=None):
    if force is None:
        force = False
    if debug is None:
        debug = False

    key_types = {
        "-bool": bool,
        "-float": float,
        "-float": int
    }

    key_type = next(
        (k for k, t in key_types.iteritems() if isinstance(value, t)),
        "-string"
    )

    args = ["defaults", "write"] + (["-f"] if force else [])
    args += [domain, key, key_type, str(value)]
    _spawn(args, debug=debug)


def _make_symlink(source, target, debug=None, force=None):
    linked = False

    if not os.path.exists(source):
        raise SymlinkError(
            "symlink source \"{0}\" does not exist".format(
                _collapseuser(source)
            )
        )

    try:
        os.symlink(source, target)
        linked = True
        tty.puts("symlinked {0} -> {1}".format(
            tty.color(_collapseuser(target), tty.MAGENTA),
            _collapseuser(source)
        ))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

        if os.path.islink(target):
            if os.path.samefile(
                os.path.realpath(target),
                os.path.realpath(source)
            ):
                linked = True
                tty.putdebug("Already linked: {0} -> {1}".format(
                    tty.color(_collapseuser(target), tty.MAGENTA),
                    _collapseuser(source)
                ), debug)
            else:
                fmt = "Linked to wrong target: {0} -> {1} (instead of {2})"
                tty.puterr(fmt.format(
                    tty.color(target, tty.MAGENTA),
                    os.path.realpath(_collapseuser(target)),
                    os.path.realpath(_collapseuser(source))
                ), warning=force)
        else:
            tty.puterr("{0} symlink target already exists at: {1}".format(
                _collapseuser(source),
                _collapseuser(target)
            ), warning=force)

    if not linked and force:
        try:
            osx.move_to_trash(target)
            print(tty.progress("Moved {0} to trash").format(target))
        except OSError as e:
            tty.puterr("Error moving {0} to trash: {1}".format(target, str(e)))
            return False
        return _make_symlink(source, target, debug, force)

    return linked


def _remove_dead_targets(targets, debug=None):
    for target in targets:
        if os.path.islink(target) and os.path.samefile(
            CIDER_DIR,
            os.path.commonprefix([CIDER_DIR, os.path.realpath(target)]),
        ):
            os.remove(target)
            print(tty.progress("Removed dead symlink: {0}".format(
                _collapseuser(target))
            ))


def _collapseuser(path):
    home_dir = os.environ.get("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    if os.path.samefile(home_dir, os.path.commonprefix([path, home_dir])):
        return os.path.join("~", os.path.relpath(path, home_dir))
    return path


def _apply_icon(app, icon, debug=None):
    app_path = osx.path_for_app(app)
    if not app_path:
        raise AppMissingError("Application not found: '{0}'".format(app))

    try:
        components = urlparse(icon)
        tmpdir = mkdtemp()
        icon_path = os.path.join(tmpdir, os.path.basename(components["path"]))
        print(tty.progress("Downloading {0} icon: {1}".format(app, icon)))
        _curl(icon, icon_path)
    except ValueError:
        icon_path = icon

    osx.set_icon(app_path, icon_path)


def restore(debug=None):
    if debug is None:
        debug = False
    macos_version = platform.mac_ver()[0]

    if int(macos_version.split(".")[1]) < 9:
        raise UnsupportedOSError(
            "Unsupported OS version; please upgrade to 10.9 or later " +
            "and try again.",
            macos_version
        )
    elif not os.path.isdir("/Applications/Xcode.app"):
        raise XcodeMissingError(
            "Xcode not installed",
            "https://itunes.apple.com/us/app/xcode/id497799835?mt=12"
        )
    elif _spawn(["which", "brew"], check_call=False, debug=debug,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        raise BrewMissingError(
            "Homebrew not installed",
            "http://brew.sh/#install"
        )

    bootstrap = _read_bootstrap()
    casks = bootstrap.get("casks", [])
    formulas = bootstrap.get("formulas", [])
    dependencies = bootstrap.get("dependencies", {})

    for script in bootstrap.get("before-scripts", []):
        _spawn([script], shell=True, debug=debug, cwd=CIDER_DIR)

    for tap in bootstrap.get("taps", []):
        _spawn(["brew", "tap"] + [tap], debug=debug)

    for formula in formulas:
        if formula in dependencies:
            deps = dependencies[formula]
            deps = deps if isinstance(deps, list) else [deps]
            deps = (
                # Currently only cask dependencies are supported.
                dep.split("/")[1] for dep in deps if dep.startswith("cask/")
            )

            for cask in deps:
                _safe_install(cask, debug=debug, cask=True)
                del casks[casks.index(cask)]

        _safe_install(formula, debug=debug)

    for cask in casks:
        _safe_install(cask, debug=debug, cask=True)

    relink(debug)
    apply_defaults(debug)
    apply_icons(debug)

    for script in bootstrap.get("after-scripts", []):
        _spawn([script], shell=True, debug=debug, cwd=CIDER_DIR)


def install(*formulas, **kwargs):
    formulas = list(formulas) or []
    cask = kwargs.get("cask", False)
    force = kwargs.get("force", False)
    verbose = kwargs.get("verbose", False)
    debug = kwargs.get("debug", False)

    args = ["brew"] + (["cask"] if cask else [])
    args += ["install"] + formulas + (["--force"] if force else [])
    args += (["-v"] if verbose else [])
    args += (["-d"] if debug else [])
    _spawn(args, debug=debug)

    for formula in formulas:
        if _modify_bootstrap(
            "casks" if cask else "formulas",
            transform=lambda x: x + [formula] if formula not in x else x
        ):
            tty.puts("Added {0} to bootstrap".format(formula))
        else:
            tty.puterr(
                "{0} already bootstrapped; skipping install".format(formula),
                warning=True
            )


def rm(*formulas, **kwargs):
    formulas = list(formulas) or []
    cask = kwargs.get("cask", False)
    verbose = kwargs.get("verbose", False)
    debug = kwargs.get("debug", False)

    args = ["brew"] + (["cask"] if cask else [])
    args += ["zap" if cask else "rm"] + formulas
    args += (["-v"] if verbose else [])
    args += (["-d"] if debug else [])
    _spawn(args, check_call=False)

    for formula in formulas:
        if _modify_bootstrap(
            "casks" if cask else "formulas",
            transform=lambda xs: [x for x in xs if x != formula]
        ):
            tty.puts("Removed {0} from bootstrap".format(formula))
        else:
            tty.puterr("{0} not found in bootstrap".format(formula))


def tap(tap, verbose=None, debug=None):
    if verbose is None:
        verbose = False
    if debug is None:
        debug = False

    args = ["brew", "tap"] + ([tap] if tap is not None else [])
    args += (["-v"] if verbose else [])
    args += (["-d"] if debug else [])
    _spawn(args, debug=debug)

    if tap is not None:
        if _modify_bootstrap(
            "taps",
            transform=lambda x: x + [tap] if tap not in x else x
        ):
            tty.puts("Added {0} tap to bootstrap".format(tap))
        else:
            tty.puterr("{0} tap already bootstrapped".format(tap))


def untap(tap, verbose=None, debug=None):
    if verbose is None:
        verbose = False
    if debug is None:
        debug = False

    args = ["brew", "untap", tap]
    args += (["-v"] if verbose else [])
    args += (["-d"] if debug else [])
    _spawn(args, debug=debug)

    if _modify_bootstrap(
        "taps",
        transform=lambda xs: [x for x in xs if x != tap]
    ):
        tty.puts("Removed {0} tap from bootstrap".format(tap))
    else:
        tty.puterr("{0} tap not found in bootstrapped".format(tap))


def relink(debug=None, force=None):
    if debug is None:
        debug = False
    if force is None:
        force = False

    symlinks = _read_bootstrap().get("symlinks", {})
    previous_targets = _read_json(SYMLINK_TARGETS_FILE, [])
    new_targets = []

    for source_glob, target in symlinks.iteritems():
        _mkdir_p(os.path.dirname(os.path.expanduser(target)))
        for source in glob.iglob(os.path.join(SYMLINK_DIR, source_glob)):
            source = os.path.join(CIDER_DIR, source)
            source_target = os.path.expanduser(target)
            if target.endswith(os.path.sep) or target == "~":
                source_target = os.path.join(
                    source_target,
                    os.path.basename(source)
                )

            _make_symlink(source, source_target, debug, force)
            new_targets.append(source_target)

    _remove_dead_targets(set(previous_targets) - set(new_targets), debug)
    _mkdir_p(os.path.dirname(SYMLINK_TARGETS_FILE))
    _write_json(SYMLINK_TARGETS_FILE, sorted(new_targets))


def installed(cask=None):
    if cask is None:
        cask = False
    bootstrap = _read_bootstrap()
    key = "casks" if cask else "formulas"
    return bootstrap.get(key, [])


def missing(cask=None, debug=None):
    formulas = [item.split()[0].strip() for item in installed(cask)]
    args = ["brew"] + (["cask"] if cask else []) + ["ls", "-1"]
    brewed = _spawn(args, check_output=True, debug=debug).strip().split("\n")

    def brew_orphan(dependency):
        args = ["brew"] + (["cask"] if cask else [])
        args += ["uses", "--installed", "--recursive", dependency]
        uses = _spawn(args, check_output=True, debug=debug).split()
        return len(set(formulas).intersection(set(uses))) == 0

    return sorted(filter(brew_orphan, set(brewed).difference(formulas)))


def ls(formula, cask=None, debug=None):
    formulas = installed(cask)
    if formula:
        formulas = (x for x in formulas if x.startswith(formula))
    if formulas:
        print("\n".join(formulas))
    else:
        tty.puterr("nothing to list", prefix="Error")


def list_missing(cask=None, debug=None):
    if cask is None:
        cask = False
    missing_items = missing(cask, debug)
    if missing_items:
        suffix = "s" if len(missing_items) != 1 else ""
        command = "brew{0}"
        fmt = "{0} missing formula{1} (tip: try `brew uses --installed` " + \
              "to see what's using it)"
        tty.puterr(fmt.format(len(missing_items), suffix), warning=True)

        print("\n".join(missing_items) + "\n")
        sys.stdout.write("Add missing items to bootstrap? [y/N] ")

        if sys.stdin.read(1).lower() == "y":
            for formula in missing_items:
                install(formula, cask)
    else:
        print("Everything up to date.")

    return missing_items


def set_default(domain, key, value, force=None, debug=None):
    try:
        json_value = json.loads(_defaults_false_re.sub(
            "false",
            _defaults_true_re.sub("true", str(value))
        ))
    except ValueError:
        json_value = str(value)

    _write_default(domain, key, json_value, force, debug)

    def transform(defaults):
        defaults[key] = json_value
        return defaults

    if _modify_defaults(domain, transform):
        tty.puts("Updated defaults")


def remove_default(domain, key, debug=None):
    _spawn(["defaults", "delete", domain, key], debug=debug)

    def transform(defaults):
        del defaults[key]
        return defaults

    if _modify_defaults(domain, transform):
        tty.puts("Updated defaults")


def apply_defaults(debug=None):
    defaults = _read_json(DEFAULTS_FILE, {})
    for domain in defaults:
        options = defaults[domain]
        for key, value in options.iteritems():
            _write_default(domain, key, value)

    tty.puts("Applied defaults")


def run_scripts(debug=None):
    bootstrap = _read_bootstrap()
    scripts = bootstrap.get("before-scripts", []) + \
       bootstrap.get("after-scripts", [])
    for script in scripts:
        _spawn([script], shell=True, debug=debug, cwd=CIDER_DIR)


def set_icon(app, icon, debug=None):
    def transform(bootstrap):
        icons = bootstrap.get("icons", {})
        icons[app] = icon
        return bootstrap

    _modify_json(BOOTSTRAP_FILE, transform)
    _apply_icon(app, icon, debug=debug)


def remove_icon(app, debug=None):
    def transform(bootstrap):
        icons = bootstrap.get("icons", {})
        del icons[app]
        return bootstrap

    app_path = osx.path_for_app(app)
    if not app_path:
        raise AppMissingError("Application not found: '{0}'".format(app))

    _modify_json(BOOTSTRAP_FILE, transform)
    osx.remove_icon(app_path)


def apply_icons(debug=None):
    bootstrap = _read_json(BOOTSTRAP_FILE)
    icons = bootstrap.get("icons", {})
    for app, icon in icons.iteritems():
        _apply_icon(app, icon, debug)

    tty.puts("Applied icons")
