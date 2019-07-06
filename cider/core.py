# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from . import _osx as osx
from . import _tty as tty
from .exceptions import (
    UnsupportedOSError, XcodeMissingError, BrewMissingError,
    SymlinkError, AppMissingError, StowError
)
from ._lib import lazyproperty
from ._sh import (
    Brew, Defaults, spawn, collapseuser, commonpath, curl, mkdir_p,
    read_config, write_config, modify_config, isdirname, prompt
)
from fnmatch import fnmatch
from glob import iglob
from rfc3987 import parse as urlparse
from tempfile import mkdtemp
import click
import errno
import json
import os
import platform
import re
import shutil
import subprocess

_DEFAULTS_TRUE_RE = re.compile(r"\b(Y(ES)?|TRUE)\b", re.I)
_DEFAULTS_FALSE_RE = re.compile(r"\b(N(O)?|FALSE)\b", re.I)


class Cider(object):
    def __init__(self, cask=None, debug=None, verbose=None, cider_dir=None,
                 support_dir=None):
        self.cask = cask if cask is not None else False
        self.debug = debug if debug is not None else False
        self.verbose = verbose if verbose is not None else False
        self.cider_dir = cider_dir if cider_dir is not None else \
            self.fallback_cider_dir()
        self.support_dir = support_dir if support_dir is not None else \
            self.fallback_support_dir()
        self.brew = Brew(cask, debug, verbose, self.env)
        self.defaults = Defaults(debug, self.env)

    @lazyproperty
    def symlink_dir(self):
        return os.path.join(self.cider_dir, "symlinks")

    @lazyproperty
    def bootstrap_file(self):
        legacy_path = os.path.join(self.cider_dir, "bootstrap.json")
        if os.path.isfile(legacy_path):
            return legacy_path
        return os.path.join(self.cider_dir, "bootstrap.yaml")

    @lazyproperty
    def defaults_file(self):
        legacy_path = os.path.join(self.cider_dir, "defaults.json")
        if os.path.isfile(legacy_path):
            return legacy_path
        return os.path.join(self.cider_dir, "defaults.yaml")

    @lazyproperty
    def env(self):
        env = os.environ.copy()
        env.update(self.read_bootstrap().get("env", {}))
        return env

    def fallback_cider_dir(self):
        try:
            return os.path.join(os.environ["XDG_CONFIG_HOME"], "cider")
        except KeyError:
            return os.path.join(os.path.expanduser("~"), ".cider")

    def fallback_support_dir(self):
        try:
            return os.path.join(os.environ["XDG_DATA_HOME"], "cider")
        except KeyError:
            return os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "com.msanders.cider"
            )

    @lazyproperty
    def symlink_targets_file(self):
        return os.path.join(self.support_dir, "symlink_targets.json")

    def read_bootstrap(self):
        return read_config(self.bootstrap_file, {})

    def read_defaults(self):
        return read_config(self.defaults_file, {})

    def _check_cider_dir(self):
        if not os.path.isdir(self.cider_dir):
            os.mkdir(self.cider_dir)
            print(tty.progress("Created cider dir at {0}".format(
                self.cider_dir
            )))

    def _modify_bootstrap(self, key, transform=None, fallback=None):
        if transform is None:
            transform = lambda x: x  # pep8: noqa

        if fallback is None:
            fallback = []

        def outer_transform(bootstrap):
            bootstrap[key] = transform(bootstrap.get(key, fallback))
            if isinstance(bootstrap[key], list):
                bootstrap[key] = sorted(bootstrap[key])
            return bootstrap

        self._check_cider_dir()
        return modify_config(self.bootstrap_file, outer_transform)

    def _modify_defaults(self, domain, transform):
        def outer_transform(defaults):
            defaults[domain] = transform(defaults.get(domain, {}))
            return defaults

        self._check_cider_dir()
        return modify_config(self.defaults_file, outer_transform)

    def _cached_targets(self):
        return read_config(self.symlink_targets_file, [])

    def _update_target_cache(self, new_targets):
        self._check_cider_dir()
        mkdir_p(os.path.dirname(self.symlink_targets_file))
        write_config(self.symlink_targets_file, sorted(new_targets))

    def _remove_dead_targets(self, targets):
        for target in targets:
            if os.path.islink(target) and os.path.samefile(
                self.cider_dir,
                commonpath([
                    self.cider_dir,
                    os.path.realpath(target)
                ]),
            ):
                os.remove(target)
                print(tty.progress("Removed dead symlink: {0}".format(
                    collapseuser(target))
                ))

    @staticmethod
    def _remove_link_target(source, target):
        if os.path.exists(target):
            if os.path.samefile(os.path.realpath(target),
                                os.path.realpath(source)):
                os.remove(target)
            else:
                raise SymlinkError(
                    "{0} symlink target already exists at: {1}".format(
                        collapseuser(source), collapseuser(target)
                    )
                )

    def _has_xcode_tools(self):
        developer_dir = spawn(["/usr/bin/xcode-select", "-print-path"],
                              check_output=True,
                              debug=self.debug,
                              env=self.env).strip()

        return bool(os.path.isdir(developer_dir) and os.path.exists(
            os.path.join(developer_dir, "usr", "bin", "git")
        ))

    def _assert_requirements(self):
        macos_version = platform.mac_ver()[0]

        if int(macos_version.split(".")[1]) < 9:
            raise UnsupportedOSError(
                "Unsupported OS version; please upgrade to 10.9 or later "
                "and try again.",
                macos_version
            )

        if not self._has_xcode_tools():
            print(tty.progress("Installing the Command Line Tools (expect a "
                               "GUI popup):"))
            spawn(["/usr/bin/xcode-select", "--install"],
                  debug=self.debug, env=self.env)
            click.pause("Press any key when the installation is complete.")
            if not self._has_xcode_tools():
                raise XcodeMissingError(
                    "Aborted Command Line Tools installation.",
                )

        if spawn(["which", "brew"], check_call=False, debug=self.debug,
                 stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE,
                 env=self.env):
            raise BrewMissingError(
                "Homebrew not installed",
                "http://brew.sh/#install"
            )

    @staticmethod
    def _islinkkey(symlink, stow):
        return symlink == stow or symlink.startswith(os.path.join(stow, ""))

    def restore(self, ignore_errors=None):
        ignore_errors = ignore_errors if ignore_errors is not None else False
        self._assert_requirements()
        caskbrew = Brew(True, self.debug, self.verbose)
        homebrew = Brew(False, self.debug, self.verbose)

        bootstrap = self.read_bootstrap()
        casks = bootstrap.get("casks", [])
        dependencies = bootstrap.get("dependencies", {})

        self.run_scripts(before=True)

        for tap in bootstrap.get("taps", []):
            homebrew.tap(tap)

        outdated = homebrew.outdated()

        for formula in bootstrap.get("formulas", []):
            if formula in dependencies:
                deps = dependencies[formula]
                deps = deps if isinstance(deps, list) else [deps]

                # Currently only cask dependencies are supported.
                deps = (dep for dep in deps if dep.startswith("casks/"))

                for dep in deps:
                    cask = dep.split("/")[1]
                    print(tty.progress(
                        "Installing {0} dependency for {1}").format(
                            cask, formula
                        )
                    )

                    caskbrew.safe_install(cask, ignore_errors)
                    del casks[casks.index(cask)]

            homebrew.safe_install(formula, ignore_errors, formula in outdated)

        for cask in casks:
            caskbrew.safe_install(cask, ignore_errors)

        self.relink()
        self.apply_defaults()
        self.apply_icons()
        self.run_scripts(after=True)

    def install(self, *formulas, **kwargs):
        formulas = list(formulas) or []
        force = kwargs.get("force", False)

        self.brew.install(*formulas, force=force)
        self.add_to_bootstrap(formulas)

    def add_to_bootstrap(self, formulas):
        # Avoid pylint scoping warning W0640
        def transform(formula):
            return lambda x: x + [formula] if formula not in x else x

        for formula in formulas:
            if self._modify_bootstrap(
                "casks" if self.cask else "formulas",
                transform=transform(formula),
                fallback=[]
            ):
                tty.puts("Added {0} to bootstrap".format(formula))
            else:
                tty.puterr("{0} already bootstrapped; skipping install".format(
                    formula
                ), warning=True)

    def rm(self, *formulas):
        def transform(formula):
            return lambda xs: [x for x in xs if x != formula]

        formulas = list(formulas) or []
        self.brew.rm(*formulas)

        for formula in formulas:
            if self._modify_bootstrap(
                "casks" if self.cask else "formulas",
                transform=transform(formula),
                fallback=[]
            ):
                tty.puts("Removed {0} from bootstrap".format(formula))
            else:
                tty.puterr("{0} not found in bootstrap".format(formula))

    def tap(self, tap):
        if tap is None:
            tapped = self.tapped()
            if tapped:
                print("\n".join(tapped))
        else:
            self.brew.tap(tap)
            self.add_taps([tap])

    def add_taps(self, taps):
        def transform(tap):
            return lambda x: x + [tap] if tap not in x else x

        for tap in taps:
            if self._modify_bootstrap(
                "taps",
                transform=transform(tap),
                fallback=[]
            ):
                tty.puts("Added {0} tap to bootstrap".format(tap))
            else:
                tty.puterr("{0} tap already bootstrapped".format(tap))

    def untap(self, tap):
        self.brew.untap(tap)
        if self._modify_bootstrap(
            "taps",
            transform=lambda xs: [x for x in xs if x != tap],
            fallback=[]
        ):
            tty.puts("Removed {0} tap from bootstrap".format(tap))
        else:
            tty.puterr("{0} tap not found in bootstrapped".format(tap))

    @staticmethod
    def expandtarget(source, target):
        expanded = os.path.expanduser(target)
        if isdirname(target):
            return os.path.join(expanded, os.path.basename(source))
        return expanded

    def expandtargets(self, source_glob, target):
        if not isdirname(target) and ("*" in source_glob or
                                      "?" in source_glob):
            raise SymlinkError(
                "Invalid symlink: {0} => {1} (did you mean to add a "
                "trailing '/'?)".format(source_glob, target)
            )

        mkdir_p(os.path.dirname(os.path.expanduser(target)))
        sources = iglob(os.path.join(self.symlink_dir, source_glob))
        expanded = []
        for source in sources:
            source = os.path.join(self.cider_dir, source)
            source_target = self.expandtarget(source, target)

            expanded.append((source, source_target))
        return expanded

    def relink(self, force=None):
        force = force if force is not None else False
        symlinks = self.read_bootstrap().get("symlinks", {})
        old_targets = self._cached_targets()
        new_targets = []

        for source_glob, target in symlinks.items():
            for source, expanded_target in self.expandtargets(source_glob,
                                                              target):
                if self.mklink(source, expanded_target, force):
                    new_targets.append(expanded_target)

        self._remove_dead_targets(set(old_targets) - set(new_targets))
        self._update_target_cache(new_targets)
        return new_targets

    def mklink(self, source, target, force=None):
        linked = False

        if not os.path.exists(source):
            raise SymlinkError(
                "symlink source \"{0}\" does not exist".format(
                    collapseuser(source)
                )
            )

        try:
            os.symlink(source, target)
            linked = True
            tty.puts("symlinked {0} -> {1}".format(
                tty.color(collapseuser(target), tty.MAGENTA),
                collapseuser(source)
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
                        tty.color(collapseuser(target), tty.MAGENTA),
                        collapseuser(source)
                    ), self.debug)
                else:
                    fmt = "Linked to wrong target: {0} -> {1} (instead of {2})"
                    tty.puterr(fmt.format(
                        tty.color(target, tty.MAGENTA),
                        os.path.realpath(collapseuser(target)),
                        os.path.realpath(collapseuser(source))
                    ), warning=force)
            else:
                tty.puterr("{0} symlink target already exists at: {1}".format(
                    collapseuser(source),
                    collapseuser(target)
                ), warning=force)

        if not linked and force:
            try:
                osx.move_to_trash(target)
                print(tty.progress("Moved {0} to trash").format(target))
            except OSError as e:
                tty.puterr("Error moving {0} to trash: {1}".format(
                    target, str(e))
                )
                return False
            return self.mklink(source, target, force)

        return linked

    def installed(self, prefix=None):
        bootstrap = self.read_bootstrap()
        key = "casks" if self.cask else "formulas"
        formulas = bootstrap.get(key, [])
        if prefix:
            return [x for x in formulas if x.startswith(prefix)]
        return formulas

    def tapped(self):
        return self.read_bootstrap().get("taps", [])

    def missing(self):
        # The packages currently in the bootstrap file
        installed = [item.split()[0].strip() for item in self.installed()]
        # List of packages installed on the system
        brewed = self.brew.ls()

        def brew_orphan(formula):
            # Temporary workaround to avoid bug with brew-pip.
            # https://github.com/msanders/cider/issues/25
            if formula.startswith("pip-"):
                return False
            if self.cask:
                # If the formula is not in bootstrap file
                # return True so we can add the formula to the
                # bootstrap file
                return formula not in installed
            uses = self.brew.uses(formula)
            return len(set(installed) & set(uses)) == 0

        return sorted(filter(brew_orphan, set(brewed) - set(installed)))

    def missing_taps(self):
        bootstrapped = self.tapped()
        brewed = self.brew.tap().strip().splitlines()
        return sorted(set(brewed) - set(bootstrapped))

    def ls(self, formula):
        formulas = self.installed(formula)
        if formulas:
            print("\n".join(formulas))
        else:
            tty.puterr("nothing to list", prefix="Error")

    def list_missing(self):
        missing_items = self.missing()
        if missing_items:
            suffix = "s" if len(missing_items) != 1 else ""
            fmt = "{0} missing formula{1} (tip: try `brew uses " + \
                  "--installed` to see what's using it)"
            tty.puterr(fmt.format(len(missing_items), suffix), warning=True)
            print("\n".join(missing_items) + "\n")

            if prompt("Add to bootstrap? [y/N] "):
                self.add_to_bootstrap(missing_items)
        else:
            print("Everything up to date.")

    def list_missing_taps(self):
        missing_taps = self.missing_taps()
        if missing_taps:
            suffix = "s" if len(missing_taps) != 1 else ""
            fmt = "{0} missing tap{1}"
            tty.puterr(fmt.format(len(missing_taps), suffix), warning=True)
            print("\n".join(missing_taps) + "\n")

            if prompt("Add to bootstrap? [y/N] "):
                self.add_taps(missing_taps)
        else:
            print("Everything up to date.")

    @staticmethod
    def json_value(value):
        if isinstance(value, str) or isinstance(value, unicode):
            try:
                return json.loads(_DEFAULTS_FALSE_RE.sub(
                    "false",
                    _DEFAULTS_TRUE_RE.sub("true", value)
                ))
            except ValueError:
                pass
        return value

    def set_default(self, domain, key, value, force=None):
        json_value = self.json_value(value)
        self.defaults.write(domain, key, json_value, force)

        def transform(defaults):
            defaults[key] = json_value
            return defaults

        if self._modify_defaults(domain, transform):
            tty.puts("Updated defaults")

    def remove_default(self, domain, key):
        self.defaults.delete(domain, key)

        def transform(defaults):
            defaults.pop(key, None)
            return defaults

        if self._modify_defaults(domain, transform):
            tty.puts("Updated defaults")

    def apply_defaults(self):
        defaults = self.read_defaults()
        for domain, options in defaults.items():
            for key, value in options.items():
                self.defaults.write(domain, key, value)

        tty.puts("Applied defaults")

    def run_scripts(self, before=None, after=None):
        bootstrap = self.read_bootstrap()
        scripts = []
        scripts += bootstrap.get("before-scripts", []) if before else []
        scripts += bootstrap.get("after-scripts", []) if after else []
        for script in scripts:
            spawn([script], shell=True, debug=self.debug,
                  cwd=self.cider_dir, env=self.env)

    def set_icon(self, app, icon):
        def transform(icons):
            icons[app] = icon
            return icons

        self._modify_bootstrap("icons", transform, {})
        _apply_icon(app, icon)

    def remove_icon(self, app):
        def transform(icons):
            if icons:
                del icons[app]
            return icons

        app_path = osx.path_for_app(app)
        if not app_path:
            raise AppMissingError("Application not found: '{0}'".format(app))

        self._modify_bootstrap("icons", transform)
        osx.remove_icon(app_path)

    def apply_icons(self):
        bootstrap = read_config(self.bootstrap_file)
        icons = bootstrap.get("icons", {})
        for app, icon in icons.items():
            _apply_icon(app, icon)

        tty.puts("Applied icons")

    def add_symlink(self, name, target):
        target = collapseuser(os.path.normpath(target))
        target_dir = os.path.dirname(target)

        # Add trailing slash for globbing.
        if target_dir != "~":
            target_dir = os.path.join(target_dir, "")

        def transform(symlinks):
            for key in symlinks:
                if (os.path.dirname(key) == name and
                   fnmatch(os.path.basename(target), os.path.basename(key))):
                    return symlinks

            dotted = os.path.basename(target).startswith(".")
            pattern = "{0}/{1}*".format(name, "." if dotted else "")
            symlinks[pattern] = target_dir
            return symlinks

        return self._modify_bootstrap("symlinks", transform, {})

    def remove_symlink(self, name):
        def transform(symlinks):
            if symlinks:
                to_delete = []
                for key in symlinks.keys():
                    if self._islinkkey(key, name):
                       to_delete.append(key)
                for key in to_delete:
                    del symlinks[key]
            return symlinks

        return self._modify_bootstrap("symlinks", transform)

    def addlink(self, name, *items):
        for item in items:
            stow_path = os.path.join(self.symlink_dir, name)
            stow_fpath = os.path.join(stow_path, os.path.basename(item))
            if not os.path.exists(item):
                raise StowError(
                    "Can't link {0}: No such file or directory".format(
                        collapseuser(item)
                    )
                )

            samefile = os.path.exists(stow_fpath) and os.path.samefile(
                os.path.realpath(stow_fpath), os.path.realpath(item)
            )

            if os.path.exists(stow_fpath) and not samefile:
                raise StowError("Link already exists at {0}".format(
                    collapseuser(stow_fpath)
                ))

            if not samefile:
                mkdir_p(stow_path)
                shutil.move(item, stow_path)

            target = os.path.abspath(item)
            self.add_symlink(name, target)
            self.mklink(stow_fpath, target)
            self._update_target_cache(self._cached_targets() + [target])

    def unlink(self, name):
        symlinks = self.read_bootstrap().get("symlinks", {})

        removed_targets = set()
        found = False
        for source_glob, target in symlinks.items():
            if self._islinkkey(source_glob, name):
                found = True
                for source, target in self.expandtargets(source_glob, target):
                    self._remove_link_target(source, target)
                    removed_targets.add(target)
                    shutil.move(source, target)
                    print(tty.progress("Moved {0} -> {1}".format(
                        collapseuser(source),
                        collapseuser(target)
                    )))

        if not found:
            raise StowError("No symlink found with name: {0}".format(name))

        try:
            os.rmdir(os.path.join(self.symlink_dir, name))
        except OSError as e:
            if e.errno != errno.ENOTEMPTY:
                raise e

        self.remove_symlink(name)
        self._update_target_cache(
            set(self._cached_targets()) - removed_targets
        )


def _apply_icon(app, icon):
    app_path = osx.path_for_app(app)
    if not app_path:
        raise AppMissingError("Application not found: '{0}'".format(app))

    try:
        components = urlparse(icon)
        if not components["scheme"] or components['scheme'] == "file":
            icon_path = components["path"]
        else:
            tmpdir = mkdtemp()
            icon_path = os.path.join(tmpdir,
                                     os.path.basename(components["path"]))
            print(tty.progress("Downloading {0} icon: {1}".format(app, icon)))
            curl(icon, icon_path)
    except ValueError:
        icon_path = icon

    osx.set_icon(app_path, os.path.expanduser(icon_path))
