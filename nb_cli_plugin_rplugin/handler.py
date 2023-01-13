import re
import asyncio
from typing import List, Tuple, Optional

from rich.live import Live
from rich.text import Text
from rich.tree import Tree
from rich.panel import Panel
from rich.style import Style
from rich.syntax import Syntax
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from nb_cli.handlers import call_pip_install

from . import _
from .manager import _init, get_version, parse_depends_tree
from .meta import (
    Plugin,
    get_pypi_meta,
    get_pypi_meta_retry,
    get_github_statistics,
)

REPO_REGEX = r"^https:\/\/github\.com\/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)$"
REPO_REGEX_INCLUDE_PATH = (
    r"^https:\/\/github\.com\/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)"
)
console = Console()

# i18n
AUTHOR = _('Author')
PACKAGE = _('Package')
HOMEPAGE = _('Homepage')


def _parse_homepage(address: str) -> Text:
    text = match[1] if (match := re.match(REPO_REGEX, address)) else address
    return Text(text, style=Style(link=address))


def _make_panel(plugin: Plugin) -> Panel:
    message = Text(plugin.desc + "\n\n", no_wrap=False, overflow="ellipsis")
    message.append(
        Text(" ").join(
            Text(tag.label, style=f"reverse {tag.color}")
            for tag in plugin.tags
        )
    )

    author = Text(f"\n\n{AUTHOR}: ")
    author.append(f"{plugin.author}\n", "medium_purple1")
    message.append(author)

    package = Text(f"{PACKAGE}: ", no_wrap=False)
    package.append(f"{plugin.project_link}\n", "bold light_goldenrod3")
    message.append(package)

    message.append(f"{HOMEPAGE}: ")
    message.append(_parse_homepage(plugin.homepage))
    return Panel(
        message,
        title=f"[blue]{plugin.name}{'✅' if plugin.is_official else ''}[/blue]",
        subtitle=plugin.module_name,
        width=60,
    )


def print_plugins(
    plugins: List[Plugin], count: int = 10, page: int = 1
) -> Tuple[int, List[Plugin]]:
    page_ = page - 1
    show_plugins = plugins[page_ * count : page * count]

    pages, no_include_plugins = divmod(len(plugins), count)
    pages = pages + bool(no_include_plugins)
    console.print(
        Columns(
            (_make_panel(plugin) for plugin in show_plugins),
            align="center",
            title="NoneBot {store}({page}/{pages})".format(
                store=_('Store'), page=page, pages=pages
            ),
        ),
        emoji=True,
    )
    return pages, show_plugins


async def print_plugin_detail(
    plugin: Plugin,
    disable_github: bool,
    disable_pypi: bool,
):
    # sourcery skip: use-fstring-for-concatenation, use-fstring-for-formatting
    message = Text(
        plugin.desc + "\n\n🔖{}:\n".format(_("Tags")),
        no_wrap=False,
        overflow="fold",
    )
    message.append(
        Text(" ").join(
            Text(tag.label, style=f"reverse {tag.color}")
            for tag in plugin.tags
        )
    )

    author = Text(f"\n\n👤{AUTHOR}: ")
    author.append(f"{plugin.author}\n", "medium_purple1")
    message.append(author)

    package = Text(f"📦{PACKAGE}: ", no_wrap=False)
    package.append(f"{plugin.project_link}\n", "bold light_goldenrod3")
    message.append(package)

    module = Text("📦{}: ".format(_("Module Name")), no_wrap=False)
    module.append(f"{plugin.module_name}\n", "bold light_goldenrod3")
    message.append(module)

    homepage = Text(f"🏠{HOMEPAGE}: ")
    homepage.append(plugin.homepage, Style(link=plugin.homepage))
    message.append(homepage)

    with Live(
        Panel(
            message,
            title=Text(
                f"{plugin.name}{'✅' if plugin.is_official else ''}",
                style="blue",
            ),
        )
    ):
        if not disable_pypi:
            try:
                pypi = await get_pypi_meta(plugin.project_link)
                message.append("\n\n🍱{}:\n".format(_('PyPI metadata')))

                version = Text("{}: ".format(_('Version')))
                version.append(f"{pypi.version}\n", "chartreuse1")
                message.append(version)

                keywords = Text("{}: ".format(_('Keywords')))
                keywords.append(f"{pypi.keywords}\n", "chartreuse1")
                message.append(keywords)

                requires = Text("{}: ".format(_('Requires Python')))
                requires.append(pypi.requires_python, "chartreuse1")
                message.append(requires)
            except Exception as e:
                message.append(
                    Text(f"\n\n[{e.__class__.__name__}] {str(e)}", style="red")
                )

        if not disable_github and (
            match := re.match(REPO_REGEX_INCLUDE_PATH, plugin.homepage)
        ):
            try:
                repo = await get_github_statistics(match[1])
                message.append("\n\n🐙{}:\n".format(_('GitHub statistics')))

                star = Text(f"Stars: {repo.stargazers_count}\n")
                star.stylize("chartreuse1", 7)
                message.append(star)

                issues = Text(f"Issues/PRs: {repo.open_issues_count}\n")
                issues.stylize("chartreuse1", 12)
                message.append(issues)

                forks = Text(f"Forks: {repo.forks_count}")
                forks.stylize("chartreuse1", 7)
                message.append(forks)

                if repo.license:
                    license_ = Text("\nLicense: ")
                    license_.append(
                        f"{repo.license.name}({repo.license.spdx_id})",
                        "chartreuse1",
                    )
                    message.append(license_)
            except Exception as e:
                message.append(
                    Text(f"\n\n[{e.__class__.__name__}] {str(e)}", style="red")
                )


def print_markdown(markdown: str):
    console.print(Markdown(markdown, code_theme="github-dark"))


def print_syntax(code: str):
    console.print(Syntax(code, "reStructuredText"))


async def install_plugin(
    plugins: List[Plugin], pypi_args: Optional[List[str]]
):
    proc = await call_pip_install(
        [plugin.project_link for plugin in plugins], pypi_args
    )
    await proc.wait()


async def print_dependencies_tree(plugins: List[Plugin]):
    await _init()
    root = Tree(":open_file_folder: This Project")

    async def _print(plugin: Plugin):
        try:
            pypi_metadata = await get_pypi_meta_retry(
                plugin.project_link, time=2
            )
        except Exception as e:
            tree = Tree(
                Text(
                    f"{plugin.project_link} "
                    f"[{e.__class__.__name__}] {str(e)}",
                    style="red",
                )
            )
        else:
            tree = await parse_depends_tree(
                plugin,
                pypi_metadata,
                await get_version(plugin.module_name),
            )
        root.add(tree)

    with Live(root):
        await asyncio.gather(
            *[asyncio.create_task(_print(plugin)) for plugin in plugins]
        )
