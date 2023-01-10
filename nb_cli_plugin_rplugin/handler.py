import re

from rich.text import Text
from rich.panel import Panel
from rich.style import Style
from rich.columns import Columns
from rich.console import Console

from .meta import Plugin, get_plugins

REPO_REGEX = r"^https:\/\/github\.com\/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)$"


def _parse_homepage(address: str) -> Text:
    text = match[1] if (match := re.match(REPO_REGEX, address)) else address
    return Text(text, style=Style(link=address))


def _make_panel(plugin: Plugin) -> Panel:
    message = Text(plugin.desc + "\n\n", no_wrap=False, overflow="fold")
    message.append(
        Text(" ").join(
            Text(tag.label, style=f"reverse {tag.color}")
            for tag in plugin.tags
        )
    )

    author = Text(f"\n\nAuthor: {plugin.author}\n")
    author.stylize("medium_purple1", 10)
    message.append(author)

    package = Text(f"Package: {plugin.project_link}\n", no_wrap=False)
    package.stylize("bold light_goldenrod3", 9)
    message.append(package)

    message.append("Homepage: ")
    message.append(_parse_homepage(plugin.homepage))
    return Panel(
        message,
        title=f"[blue]{plugin.name}{'✅' if plugin.is_official else ''}[/blue]",
        subtitle=plugin.module_name,
        width=60,
    )


async def print_plugins(count: int = 10, page: int = 1):
    plugins = await get_plugins()
    page_ = page - 1
    show_plugins = plugins[page_ * count : page * count]
    console = Console()
    console.print(
        Columns(
            (_make_panel(plugin) for plugin in show_plugins),
            align="center",
            title=f"[red]NoneBot 商店({page}/{len(plugins)//count})[/red]",
        ),
        emoji=True,
    )
