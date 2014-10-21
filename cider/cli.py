# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from cider import Cider
from subprocess import CalledProcessError
from webbrowser import open as urlopen
import _tty as tty
import cider
import click
import sys


class CLI(click.Group):
    def __init__(self, **attrs):
        click.Group.__init__(self, **attrs)

    def format_usage(self, ctx, formatter):
        pass

    def format_options(self, ctx, formatter):
        rows = [
            "{0} [cask] install FORMULA...",
            "{0} [cask] rm FORMULA...",
            "{0} [cask] list",
            "{0} [cask] missing",
            "{0} set-default [-g] NAME KEY VALUE",
            "{0} remove-default [-g] NAME KEY",
            "{0} apply-defaults",
            "{0} set-icon APP ICON",
            "{0} remove-icon APP",
            "{0} apply-icons",
            "{0} run-scripts",
            "{0} restore",
            "{0} relink"
        ]

        basename = ctx.command_path
        with formatter.section('Example usage'):
            formatter.write_dl((row.format(basename), '') for row in rows)

    def get_command(self, ctx, cmd_name):
        aliases = {
            "delete": "remove-default",
            "ls": "list",
            "write": "set-default"
        }

        cmd_name = aliases.get(cmd_name, cmd_name)
        return click.Group.get_command(self, ctx, cmd_name)


@click.command(cls=CLI)
def cli():
    pass


@cli.command()
@click.argument("command")
@click.argument("arg", required=False, nargs=-1)
@click.option("-f", "--force", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cask(ctx, command, arg, force=None, verbose=None, debug=None):
    func_by_cmd = {
        "install": cask_install,
        "rm": cask_rm,
        "missing": cask_missing,
        "list": cask_list
    }

    aliases = {
        "ls": "list",
    }

    args_by_cmd = {
        "install": ["formula", "force", "verbose", "debug"],
        "rm": ["formula", "verbose", "debug"],
        "missing": ["debug"],
        "list": []
    }

    cmd = aliases.get(command, command)
    args = args_by_cmd.get(cmd, [])
    kwargs = {
        "formula": arg,
        "force": force,
        "verbose": verbose,
        "debug": debug
    }
    kwargs = {k: v for k, v in kwargs.iteritems() if k in args}

    func = func_by_cmd.get(cmd)
    if func:
        ctx.invoke(func, **kwargs)
    else:
        raise click.ClickException("No such command \"{0}\"".format(cmd))


@cli.command()
@click.option("-d", "--debug", is_flag=True)
def restore(debug=None):
    Cider(debug).restore()


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def install(formula, debug=None, verbose=None, force=None):
    Cider(debug, verbose).install(force=force, *formula)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def rm(formula, debug=None, verbose=None):
    Cider(debug, verbose).rm(*formula)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("tap", required=False)
def tap(tap, debug=None, verbose=None):
    Cider(debug, verbose).tap(tap)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("tap")
def untap(tap, debug=None, verbose=None):
    Cider(debug, verbose).untap(tap)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-f", "--force", is_flag=True)
def relink(debug=None, force=None):
    Cider(debug).relink(force=force)


@cli.command("list")
@click.argument("formula", required=False)
def ls(formula):
    Cider().ls(formula)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
def missing(debug=None):
    Cider(debug).list_missing()


@cli.command("cask install")
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def cask_install(formula, force=None, debug=None, verbose=None):
    Cider(True, debug, verbose).install(*formula, force=force)


@cli.command("cask rm")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def cask_rm(formula, debug=None, verbose=None):
    Cider(True, debug, verbose).rm(*formula)


@cli.command("cask list")
@click.argument("formula", required=False)
def cask_list(formula):
    Cider(cask=True).ls(formula)


@cli.command("cask missing")
@click.option("-d", "--debug", is_flag=True)
def cask_missing(debug=None):
    Cider(True, debug).list_missing()


@cli.command("set-default")
@click.argument("name")
@click.argument("key")
@click.argument("value")
@click.option("-g", "--globalDomain", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.option("-int", is_flag=True, expose_value=False)
@click.option("-float", is_flag=True, expose_value=False)
@click.option("-string", is_flag=True, expose_value=False)
@click.option("-bool", is_flag=True, expose_value=False)
def set_default(name, key, value, globaldomain=None, force=None, debug=None):
    if globaldomain:
        name, key, value = "NSGlobalDomain", name, key
    Cider(debug).set_default(
        name,
        key,
        value,
        force=force
    )


@cli.command("remove-default")
@click.option("-g", "--globalDomain", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.argument("name")
@click.argument("key", required=False)
def remove_default(name, key, globaldomain=None):
    if globaldomain:
        name, key = "NSGlobalDomain", name
    Cider().remove_default(name, key)


@cli.command("apply-defaults")
@click.option("-d", "--debug", is_flag=True)
def apply_defaults(debug=None):
    Cider(debug).apply_defaults()


@cli.command("set-icon")
@click.argument("app")
@click.argument("icon")
def set_icon(app, icon):
    Cider().set_icon(app, icon)


@cli.command("remove-icon")
@click.argument("app")
def remove_icon(app):
    Cider().remove_icon(app)


@cli.command("apply-icons")
def apply_icons():
    Cider().apply_icons()


@cli.command("run-scripts")
@click.option("-d", "--debug", is_flag=True)
def run_scripts(debug=None):
    Cider(debug).run_scripts()


def main():
    try:
        cli.main(standalone_mode=False)
    except CalledProcessError as e:
        tty.puterr("`{0}` failed with code {1}".format(
            " ".join(e.cmd),
            e.returncode
        ))
    except cider.JSONError as e:
        tty.puterr("Error reading JSON at {0}: {1}".format(
            e.filepath,
            e.message
        ))
    except cider.XcodeMissingError as e:
        print("First, you need to install Xcode (press any key to redirect)")
        click.getchar()
        urlopen(e.url)
        sys.exit(1)
    except cider.BrewMissingError as e:
        print("Next, install Homebrew (press any key to redirect)")
        click.getchar()
        urlopen(e.url)
        sys.exit(1)
    except (cider.CiderException, click.ClickException) as e:
        tty.puterr(e.message, prefix="Error:")
        sys.exit(e.exit_code)
    except click.Abort:
        sys.stderr.write("Aborted!\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
