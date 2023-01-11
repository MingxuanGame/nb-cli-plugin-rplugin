from typing import List, Optional, cast

import click
from noneprompt import Choice, ListPrompt, InputPrompt, CancelledError
from nb_cli.cli import (
    CLI_DEFAULT_STYLE,
    ClickAliasedGroup,
    run_sync,
    run_async,
)

from .handler import print_plugins
from .meta import Plugin, get_plugins, search_plugins


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


async def _prompt_choice_page(
    ctx: click.Context, plugins: List[Plugin], count: int, page: int
):
    all_pages = print_plugins(plugins, count, page)

    async def _next_page():
        nonlocal page
        page += 1

    async def _previous_page():
        nonlocal page
        page -= 1

    async def _choose_specified_page():
        nonlocal page
        try:
            _page = await InputPrompt(
                f"Page to go({page}/{all_pages}):",
                validator=lambda x: 1 <= int(x) <= all_pages
                if x.isdigit()
                else False,
            ).prompt_async(
                style=CLI_DEFAULT_STYLE,
            )
        except CancelledError:
            ctx.exit()
        page = int(_page)

    all_choices = [
        Choice(
            "See the previous page.",
            _previous_page,
        ),
        Choice(
            "See the next page.",
            _next_page,
        ),
    ]
    choose_page_choice = Choice(
        "Go to the specified page.", _choose_specified_page
    )

    while True:
        if all_pages == 1:
            # 只有一页
            ctx.exit()
        elif page == 1:
            # 在第一页
            choices = [all_choices[1], choose_page_choice]
        elif page == all_pages:
            # 在最后一页
            choices = [all_choices[0], choose_page_choice]
        else:
            choices = all_choices[:]
            choices.append(choose_page_choice)
        try:
            result = await ListPrompt(
                "What do you want to do next?",
                choices=choices,
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        except CancelledError:
            ctx.exit()

        click.clear()
        await result.data()
        print_plugins(plugins, count, page)


@rplugin.command()
@click.pass_context
@click.option(
    "-c", "--count", default=10, help="The count of plugins in a page."
)
@click.option("-p", "--page", default=1, help="The specified page of plugins.")
@run_async
async def list(
    ctx: click.Context,
    count: int,
    page: int,
):
    """List all plugins in store"""
    await _prompt_choice_page(ctx, await get_plugins(), count, page)


@rplugin.command()
@click.pass_context
@click.argument("name", nargs=1, required=False, default=None)
@click.option(
    "-c", "--count", default=10, help="The count of plugins in a page."
)
@click.option("-p", "--page", default=1, help="The specified page of plugins.")
@run_async
async def search(
    ctx: click.Context, name: Optional[str], count: int, page: int
):
    if name is None:
        name = await InputPrompt("Plugin name to search:").prompt_async(
            style=CLI_DEFAULT_STYLE
        )
    await _prompt_choice_page(
        ctx, search_plugins(await get_plugins(), name), count, page
    )
