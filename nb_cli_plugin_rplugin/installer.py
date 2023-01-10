from typing import cast

from nb_cli.cli import CLIMainGroup, cli

from .cli import rplugin


def install():
    cli_ = cast(CLIMainGroup, cli)
    cli_.add_command(rplugin)
