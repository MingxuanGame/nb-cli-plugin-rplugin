from typing import List, cast

import click
from noneprompt import Choice, ListPrompt, CancelledError
from nb_cli.cli import (
    CLI_DEFAULT_STYLE,
    ClickAliasedGroup,
    run_sync,
    run_async,
)

from .handler import print_plugins


@click.group(cls=ClickAliasedGroup, invoke_without_command=True)
@click.pass_context
@run_async
async def rplugin(ctx: click.Context):
    """Manage Bot Plugin with rich text."""
    if ctx.invoked_subcommand is not None:
        return

    command = cast(ClickAliasedGroup, ctx.command)

    # auto discover sub commands and scripts
    choices: List[Choice[click.Command]] = []
    for sub_cmd_name in await run_sync(command.list_commands)(ctx):
        if sub_cmd := await run_sync(command.get_command)(ctx, sub_cmd_name):
            choices.append(
                Choice(
                    sub_cmd.help or f"Run subcommand {sub_cmd.name}",
                    sub_cmd,
                )
            )

    try:
        result = await ListPrompt(
            "What do you want to do?", choices=choices
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()

    sub_cmd = result.data
    await run_sync(ctx.invoke)(sub_cmd)


@rplugin.command()
@click.option(
    "-c", "--count", default=10, help="The count of plugins in a page."
)
@click.option("-p", "--page", default=1, help="The pages of plugins.")
@run_async
async def list(count: int, page: int):
    """List all plugins in store"""
    await print_plugins(count, page)
