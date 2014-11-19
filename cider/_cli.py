# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from . import __version__
from . import _tty as tty
from .core import Cider
from subprocess import CalledProcessError
from webbrowser import open as urlopen
import click
import sys

from .exceptions import (
    BrewMissingError, CiderException, ParserError
)

CONTEXT_SETTINGS = {"help_option_names": ['-h', '--help']}


class CLI(click.Group):
    def __init__(self, **attrs):
        click.Group.__init__(self, **attrs)

    def format_usage(self, ctx, formatter):
        pass

    def format_options(self, ctx, formatter):
        rows = [
            "{0} [cask] install FORMULA...",
            "{0} [cask] rm FORMULA...",
            "{0} [cask] list [FORMULA]",
            "{0} [cask] missing",
            "{0} tap missing",
            "{0} set-default [-g] NAME KEY VALUE",
            "{0} remove-default [-g] NAME KEY",
            "{0} addlink NAME ITEM...",
            "{0} unlink NAME",
            "{0} set-icon APP ICON",
            "{0} remove-icon APP",
            "{0} apply-defaults",
            "{0} apply-icons",
            "{0} run-scripts",
            "{0} restore",
            "{0} relink",
        ]

        basename = ctx.command_path
        with formatter.section('Example usage'):
            formatter.write_dl((row.format(basename), '') for row in rows)

    def get_command(self, ctx, command):
        aliases = {
            "delete": "remove-default",
            "ls": "list",
            "write": "set-default"
        }

        command = aliases.get(command, command)
        return click.Group.get_command(self, ctx, command)


def print_version(ctx, param, value):  # pylint: disable=W0613
    if not value or ctx.resilient_parsing:
        return
    print(__version__)
    ctx.exit()


@click.group(cls=CLI, context_settings=CONTEXT_SETTINGS)
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("--version", is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.pass_context
def cli(ctx, debug, verbose):
    ctx.obj = Cider(False, debug, verbose)


@cli.command()
@click.argument("command")
@click.argument("args", required=False, nargs=-1)
@click.option("-f", "--force", is_flag=True)
@click.pass_context
def cask(ctx, command, args, force=None):
    supported_commands = set(("install", "rm", "missing", "list"))
    aliases = {"ls": "list"}
    args_by_cmd = {
        "install": ["formulas", "force"],
        "list": ["formula"],
        "rm": ["formulas"]
    }

    kwargs = {
        "formula": args[0] if args else None,
        "formulas": args,
        "force": force
    }

    command = aliases.get(command, command)

    if command in supported_commands:
        supported_args = args_by_cmd.get(command, [])
        kwargs = {k: v for k, v in kwargs.items() if k in supported_args}
        cmd = cli.commands.get(command)
        ctx.obj = Cider(True, ctx.obj.debug, ctx.obj.verbose)
        ctx.invoke(cmd, **kwargs)
    else:
        raise click.ClickException("No such command \"{0}\"".format(command))


@cli.command()
@click.pass_obj
@click.option("-i", "--ignore-errors", is_flag=True)
def restore(cider, ignore_errors):
    cider.restore(ignore_errors=ignore_errors)


@cli.command()
@click.argument("formulas", nargs=-1, required=True)
@click.option("-f", "--force", is_flag=True)
@click.pass_obj
def install(cider, formulas, force=None):
    cider.install(*formulas, force=force)


@cli.command()
@click.argument("formulas", nargs=-1, required=True)
@click.pass_obj
def rm(cider, formulas):
    cider.rm(*formulas)


@cli.command()
@click.argument("tap", required=False)
@click.pass_obj
def tap(cider, tap):
    if tap == "missing":
        cider.list_missing_taps()
    else:
        cider.tap(tap)


@cli.command()
@click.argument("tap")
@click.pass_obj
def untap(cider, tap):
    cider.untap(tap)


@cli.command()
@click.option("-f", "--force", is_flag=True)
@click.pass_obj
def relink(cider, force=None):
    cider.relink(force=force)


@cli.command("list")
@click.argument("formula", required=False)
@click.pass_obj
def ls(cider, formula):
    cider.ls(formula)


@cli.command()
@click.pass_obj
def missing(cider):
    cider.list_missing()


@cli.command("set-default")
@click.argument("name")
@click.argument("key")
@click.argument("value")
@click.option("-g", "--globalDomain", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.option("-int", is_flag=True, expose_value=False)
@click.option("-float", is_flag=True, expose_value=False)
@click.option("-string", is_flag=True, expose_value=False)
@click.option("-bool", is_flag=True, expose_value=False)
@click.pass_obj
def set_default(cider, name, key, value, globaldomain=None, force=None):
    if globaldomain:
        name, key, value = "NSGlobalDomain", name, key
    cider.set_default(
        name,
        key,
        value,
        force=force
    )


@cli.command("remove-default")
@click.option("-g", "--globalDomain", is_flag=True)
@click.argument("name")
@click.argument("key", required=False)
@click.pass_obj
def remove_default(cider, name, key, globaldomain=None):
    if globaldomain:
        name, key = "NSGlobalDomain", name
    cider.remove_default(name, key)


@cli.command("apply-defaults")
@click.pass_obj
def apply_defaults(cider):
    cider.apply_defaults()


@cli.command("set-icon")
@click.argument("app")
@click.argument("icon")
@click.pass_obj
def set_icon(cider, app, icon):
    cider.set_icon(app, icon)


@cli.command("remove-icon")
@click.argument("app")
@click.pass_obj
def remove_icon(cider, app):
    cider.remove_icon(app)


@cli.command("apply-icons")
@click.pass_obj
def apply_icons(cider):
    cider.apply_icons()


@cli.command("run-scripts")
@click.pass_obj
def run_scripts(cider):
    cider.run_scripts(before=True, after=True)


@cli.command("addlink")
@click.argument("name")
@click.argument("items", nargs=-1, required=True)
@click.pass_obj
def addlink(cider, name, items):
    cider.addlink(name, *items)


@cli.command("unlink")
@click.argument("name")
@click.pass_obj
def unlink(cider, name):
    cider.unlink(name)


def main():
    try:
        cli.main(standalone_mode=False)
    except CalledProcessError as e:
        tty.puterr("`{0}` failed with code {1}".format(
            " ".join(e.cmd),
            e.returncode
        ))
    except ParserError as e:
        tty.puterr("Error reading {0} at {1}: {2}".format(
            e.filetype,
            e.filepath,
            e.message
        ))
    except BrewMissingError as e:
        print("Next, install Homebrew (press any key to redirect)")
        click.getchar()
        urlopen(e.url)
        sys.exit(1)
    except (CiderException, click.ClickException) as e:
        tty.puterr(e.message, prefix="Error:")
        sys.exit(e.exit_code)
    except click.Abort:
        sys.stderr.write("Aborted!\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
