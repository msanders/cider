# -*- coding: utf-8 -*-
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
            "write": "set-default",
            "delete": "remove-default"
        }

        cmd_name = aliases.get(cmd_name, cmd_name)
        return click.Group.get_command(self, ctx, cmd_name)


@click.command(cls=CLI)
@click.pass_context
def cli(ctx):
    pass


@cli.command()
@click.option("-f", "--force", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.argument("command")
@click.argument("arg", required=False, nargs=-1)
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def cask(ctx, command, arg, force=None, verbose=None, debug=None):
    funcByCommand = {
        "install": cask_install,
        "rm": cask_rm,
        "missing": cask_missing,
        "list": cask_list
    }

    argsByCommand = {
        "install": ["formula", "force", "verbose", "debug"],
        "rm": ["formula", "verbose", "debug"],
        "missing": ["debug"],
        "list": ["debug"]
    }

    args = argsByCommand.get(command, [])
    kwargs = {
        "formula": arg,
        "force": force,
        "verbose": verbose,
        "debug": debug
    }
    kwargs = {k: v for k, v in kwargs.iteritems() if k in args}

    func = funcByCommand[command]
    if func:
        ctx.invoke(func, **kwargs)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
def restore(debug=None):
    cider.restore(debug=debug)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.argument("gh-path", required=False)
def fetch(gh_path, debug=None):
    cider.fetch(gh_path, debug=debug)


@cli.command()
@click.option("-f", "--force", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def install(formula, force=None, verbose=None, debug=None):
    cider.install(*formula, force=force, debug=debug, verbose=verbose)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def rm(formula, verbose=None, debug=None):
    cider.rm(*formula, debug=debug, verbose=verbose)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("tap", required=False)
def tap(tap, verbose=None, debug=None):
    cider.tap(tap, debug=debug, verbose=verbose)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.argument("tap")
def untap(tap, verbose=None, debug=None):
    cider.untap(tap, debug=debug, verbose=verbose)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.argument("source")
@click.argument("target")
def link(source, target, debug=None):
    cider.link(source, target, debug=debug)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.argument("source")
@click.argument("target")
def unlink(source, target, debug=None):
    cider.unlink(source, target, debug=debug)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.option("-f", "--force", is_flag=True)
def relink(debug=None, force=None):
    cider.relink(debug=debug, force=force)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
@click.argument("formula", required=False)
def list(formula, debug=None):
    cider.ls(formula, debug=debug)


@cli.command()
@click.option("-d", "--debug", is_flag=True)
def missing(debug=None):
    cider.list_missing(debug=debug)


@cli.command("cask install")
@click.option("-d", "--debug", is_flag=True)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def cask_install(formula, force=None, verbose=None, debug=None):
    cider.install(
        *formula,
        cask=True,
        force=force,
        debug=debug,
        verbose=verbose
    )


@cli.command("cask rm")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.argument("formula", nargs=-1, required=True)
def cask_rm(formula, verbose=None, debug=None):
    cider.rm(*formula, cask=True, debug=debug, verbose=verbose)


@cli.command("cask list")
@click.argument("formula", required=False)
@click.option("-d", "--debug", is_flag=True)
def cask_list(formula, debug=None):
    cider.ls(formula, debug=debug, cask=True)


@cli.command("cask missing")
@click.option("-d", "--debug", is_flag=True)
def cask_missing(debug=None):
    cider.list_missing(cask=True, debug=debug)


@cli.command("set-default")
@click.option("-g", "--globalDomain", is_flag=True)
@click.option("-f", "--force", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.option("-int", is_flag=True, expose_value=False)
@click.option("-float", is_flag=True, expose_value=False)
@click.option("-string", is_flag=True, expose_value=False)
@click.option("-bool", is_flag=True, expose_value=False)
@click.argument("name")
@click.argument("key")
@click.argument("value", required=False)
def set_default(name, key, value, globaldomain=None, force=None, debug=None):
    if globaldomain:
        name, key, value = "NSGlobalDomain", name, key
    cider.set_default(
        name,
        key,
        value,
        force=force,
        debug=debug
    )


@cli.command("remove-default")
@click.option("-g", "--globalDomain", is_flag=True)
@click.option("-d", "--debug", is_flag=True)
@click.argument("name")
@click.argument("key", required=False)
def remove_default(name, key, globaldomain=None, debug=None):
    if globaldomain:
        name, key = "NSGlobalDomain", name
    cider.remove_default(name, key, debug=debug)


@cli.command("apply-defaults")
@click.option("-d", "--debug", is_flag=True)
def apply_defaults(debug=None):
    cider.apply_defaults(debug=debug)


@cli.command("set-icon")
@click.option("-d", "--debug", is_flag=True)
@click.argument("app")
@click.argument("icon")
def set_icon(app, icon, debug=None):
    cider.set_icon(app, icon, debug=debug)


@cli.command("remove-icon")
@click.option("-d", "--debug", is_flag=True)
@click.argument("app")
def remove_icon(app, debug=None):
    cider.remove_icon(app, debug=debug)


@cli.command("apply-icons")
@click.option("-d", "--debug", is_flag=True)
def apply_defaults(debug=None):
    cider.apply_icons(debug=debug)


@cli.command("run-scripts")
@click.option("-d", "--debug", is_flag=True)
def run_scripts(debug=None):
    cider.run_scripts(debug=debug)


def main():
    try:
        cli(standalone_mode=False)
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
