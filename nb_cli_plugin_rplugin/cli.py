import webbrowser
from typing import List, Optional, cast

import click
from nb_cli.config import GLOBAL_CONFIG
from nb_cli.cli import (
    CLI_DEFAULT_STYLE,
    ClickAliasedGroup,
    run_sync,
    run_async,
)
from noneprompt import (
    Choice,
    ListPrompt,
    InputPrompt,
    ConfirmPrompt,
    CancelledError,
    CheckboxPrompt,
)

from . import _
from .meta import (
    Plugin,
    get_plugins,
    get_pypi_meta,
    search_plugins,
    get_plugin_by_name,
)
from .handler import (
    print_syntax,
    print_plugins,
    install_plugin,
    print_markdown,
    print_plugin_detail,
)

# i18n
NEXT = _("What do you want to do next?")


@click.group(
    cls=ClickAliasedGroup,
    invoke_without_command=True,
    help=_("Manage Bot Plugin with rich text."),
)
@click.pass_context
@run_async
async def rplugin(ctx: click.Context):
    if ctx.invoked_subcommand is not None:
        return

    command = cast(ClickAliasedGroup, ctx.command)

    # auto discover sub commands and scripts
    choices: List[Choice[click.Command]] = []
    for sub_cmd_name in await run_sync(command.list_commands)(ctx):
        if sub_cmd := await run_sync(command.get_command)(ctx, sub_cmd_name):
            choices.append(
                Choice(
                    (
                        sub_cmd.help
                        or _("Run subcommand {}.").format(  # noqa: W503
                            sub_cmd.name
                        )
                    ),
                    sub_cmd,
                )
            )

    try:
        result = await ListPrompt(
            _("What do you want to do?"), choices=choices
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()

    sub_cmd = result.data
    await run_sync(ctx.invoke)(sub_cmd)


async def _prompt_choice_page(
    ctx: click.Context, plugins: List[Plugin], count: int, page: int
):
    all_pages, now_plugins = print_plugins(plugins, count, page)

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
                _("Page to go({page}/{all_pages}):").format(
                    page=page, all_pages=all_pages
                ),
                validator=lambda x: 1 <= int(x) <= all_pages
                if x.isdigit()
                else False,
            ).prompt_async(
                style=CLI_DEFAULT_STYLE,
            )
        except CancelledError:
            ctx.exit()
        page = int(_page)

    async def _show_plugins_detail():
        click.clear()
        try:
            result = await ListPrompt(
                _("Which plugin do you want to show?"),
                choices=[
                    Choice(f"{plugin.name} ({plugin.project_link})", plugin)
                    for plugin in now_plugins
                ],
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        except CancelledError:
            ctx.exit()

        await _detail_prompt(ctx, result.data, False, False)

    async def _install_plugins():
        click.clear()
        try:
            result = await CheckboxPrompt(
                _("Which plugin(s) do you want to install?"),
                choices=[
                    Choice(f"{plugin.name} ({plugin.project_link})", plugin)
                    for plugin in now_plugins
                ],
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        except CancelledError:
            ctx.exit()

        if plugins := [choice.data for choice in result]:
            for plugin in plugins:
                try:
                    GLOBAL_CONFIG.add_plugin(plugin.module_name)
                except RuntimeError as e:
                    click.echo(
                        _(
                            "Failed to add plugin {plugin.name} to config: {e}"
                        ).format(plugin=plugin, e=e)
                    )
            await install_plugin(plugins=plugins, pypi_args=None)
        ctx.exit()

    all_choices = [
        Choice(
            _("Previous page."),
            _previous_page,
        ),
        Choice(
            _("Next page."),
            _next_page,
        ),
    ]
    choose_page_choice = Choice(
        _("Go to the specified page."), _choose_specified_page
    )

    while True:
        if all_pages == 1:
            # 只有一页
            choices = []
        elif page == 1:
            # 在第一页
            choices = [all_choices[1], choose_page_choice]
        elif page == all_pages:
            # 在最后一页
            choices = [all_choices[0], choose_page_choice]
        else:
            choices = all_choices[:]
            choices.append(choose_page_choice)
        choices.extend(
            (
                Choice(
                    _("Show details of plugins."),
                    _show_plugins_detail,
                ),
                Choice(_("Install plugins."), _install_plugins),
            )
        )

        try:
            result = await ListPrompt(
                NEXT,
                choices=choices,
            ).prompt_async(style=CLI_DEFAULT_STYLE)
        except CancelledError:
            ctx.exit()

        click.clear()
        await result.data()
        if result.name == _("Show details of plugins."):
            break
        __, now_plugins = print_plugins(plugins, count, page)


async def _detail_prompt(
    ctx: click.Context,
    plugin: Plugin,
    disable_github: bool,
    disable_pypi: bool,
):
    await print_plugin_detail(plugin, disable_github, disable_pypi)

    async def _open_homepage():
        webbrowser.open(plugin.homepage)

    async def _open_pypi():
        webbrowser.open(f"https://pypi.org/project/{plugin.project_link}")

    async def _install_plugin():
        try:
            GLOBAL_CONFIG.add_plugin(plugin.module_name)
        except RuntimeError as e:
            click.echo(
                _("Failed to add plugin {plugin.name} to config: {e}").format(
                    plugin=plugin, e=e
                )
            )
        await install_plugin(plugins=[plugin], pypi_args=None)

    async def _print_readme():
        pypi = await get_pypi_meta(plugin.project_link)
        if pypi.description_content_type != "text/markdown":
            try:
                result = await ConfirmPrompt(
                    _(
                        "The description is not markdown. "
                        "Do you still read it by raw?"
                    ),
                    default_choice=True,
                ).prompt_async(style=CLI_DEFAULT_STYLE)
            except CancelledError:
                ctx.exit()
            if result:
                print_ = print_syntax
            else:
                ctx.exit()
        else:
            print_ = print_markdown
        click.clear()
        print_(pypi.description)

    try:
        result = await ListPrompt(
            NEXT,
            choices=[
                Choice(_("Open the homepage in the browser."), _open_homepage),
                Choice(
                    _("Open the plugin's PyPI page in the browser."),
                    _open_pypi,
                ),
                Choice(_("Read the description."), _print_readme),
                Choice(
                    _("Install the plugin."),
                    _install_plugin,
                ),
            ],
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()

    await result.data()


@rplugin.command(help=_("List all plugins in store."))
@click.pass_context
@click.option(
    "-c", "--count", default=10, help=_("The count of plugins in a page.")
)
@click.option(
    "-p", "--page", default=1, help=_("The specified page of plugins.")
)
@run_async
async def list(
    ctx: click.Context,
    count: int,
    page: int,
):
    await _prompt_choice_page(ctx, await get_plugins(), count, page)


@rplugin.command(help=_("Search plugins in store."))
@click.pass_context
@click.argument("name", nargs=1, required=False, default=None)
@click.option(
    "-c", "--count", default=10, help=_("The count of plugins in a page.")
)
@click.option(
    "-p", "--page", default=1, help=_("The specified page of plugins.")
)
@run_async
async def search(
    ctx: click.Context, name: Optional[str], count: int, page: int
):
    if name is None:
        name = await InputPrompt(_("Plugin name to search:")).prompt_async(
            style=CLI_DEFAULT_STYLE
        )
    if plugins := search_plugins(await get_plugins(), name):
        await _prompt_choice_page(ctx, plugins, count, page)
    ctx.exit(1)


@rplugin.command(help=_("Show the detail of the plugin."))
@click.argument("name", nargs=1, required=False, default=None)
@click.option(
    "--disable-github",
    required=False,
    default=False,
    help=_("Disable to show GitHub statistics."),
)
@click.option(
    "--disable-pypi",
    required=False,
    default=False,
    help=_("Disable to show PyPI metadata."),
)
@click.pass_context
@run_async
async def info(
    ctx: click.Context,
    name: Optional[str],
    disable_github: bool,
    disable_pypi: bool,
):
    if name is None:
        name = await InputPrompt(_("Plugin name to show:")).prompt_async(
            style=CLI_DEFAULT_STYLE
        )
    try:
        plugin = get_plugin_by_name(name, await get_plugins())
    except Exception:
        ctx.exit(1)
    await _detail_prompt(
        ctx,
        plugin,
        disable_github,
        disable_pypi,
    )
