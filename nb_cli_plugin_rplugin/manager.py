import sys
import json
import asyncio
import contextlib
from typing import List, Tuple, Iterable, Optional
from importlib.metadata import (
    PathDistribution,
    DistributionFinder,
    MetadataPathFinder,
    version,
)

from rich.text import Text
from rich.tree import Tree
from nb_cli.handlers import get_default_python

from .meta import Plugin, PyPIPackage, get_plugins, get_pypi_meta_retry

COLORS = ["bright_cyan", "bright_yellow", "green"]

FIRST = True
lock = asyncio.Semaphore()


class ProjectFinder(MetadataPathFinder):
    def __new__(cls, path: List[str]):
        cls.path = path
        return super().__new__(cls)

    @classmethod
    def find_distributions(
        cls, context: DistributionFinder.Context = ...
    ) -> Iterable[PathDistribution]:
        vars(context)["path"] = cls.path
        return super().find_distributions(context)


async def _init(python_path: Optional[str] = None):
    if python_path is None:
        python_path = await get_default_python()
    proc = await asyncio.create_subprocess_exec(
        python_path,
        "-W",
        "ignore",
        "-c",
        "import sys,json;print(json.dumps(sys.path[1:]))",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    sys.meta_path.append(ProjectFinder(json.loads(stdout.strip())))


async def get_version(package: str) -> Optional[str]:
    with contextlib.suppress(ImportError):
        return version(package)


async def parse_depends_tree(
    plugin: Plugin,
    pypi_meta: Optional[PyPIPackage] = None,
    plugin_ver: Optional[str] = None,
    _deep: int = 0,
) -> Tree:
    now_ver = pypi_meta.version if pypi_meta else None
    plugins = await get_plugins()
    plugins = {i.project_link: i for i in plugins}
    color = COLORS[_deep] if _deep <= 2 else COLORS[_deep - 3]
    if not pypi_meta:
        return Tree(f"[{color}]{plugin.project_link}[/{color}]")

    dependencies: List[Tuple[Plugin, PyPIPackage]] = []
    for require in pypi_meta.requires_dist or []:
        dependency = require.split(maxsplit=1)[0]
        if i := plugins.get(dependency):
            try:
                dependency_meta = await get_pypi_meta_retry(dependency)
            except Exception as e:
                return Tree(
                    Text(
                        f"{plugin.project_link} "
                        f"[{e.__class__.__name__}] {str(e)}",
                        style="red",
                    )
                )
            dependencies.append((i, dependency_meta))

    content = [f"[{color}]{plugin.project_link}[/{color}]"]
    if plugin_ver:
        if now_ver:
            if plugin_ver == now_ver:
                content.append(f" ([bold]{plugin_ver}[/bold])")
            else:
                content.append(f" ([green]{plugin_ver} {now_ver}⬆️[/green])")
        else:
            content.append(f" ({plugin_ver})")
    if _deep == 0:
        content.append(f" {plugin.desc}")
    tree = Tree("".join(content))
    for require in dependencies:
        dependency, pypi = require
        tree.add(
            await parse_depends_tree(
                dependency,
                pypi,
                await get_version(dependency.module_name),
                _deep=_deep + 1,
            )
        )
    return tree
