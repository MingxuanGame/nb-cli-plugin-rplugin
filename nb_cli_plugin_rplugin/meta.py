from typing import TYPE_CHECKING, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from nb_cli import cache
from pydantic import BaseModel
from nb_cli.exceptions import ModuleLoadFailed

from .exception import PluginNotFoundError

URLS = [
    "https://v2.nonebot.dev/plugins.json",
    "https://raw.fastgit.org/nonebot/nonebot2/master/website/static/plugins.json",  # noqa: E501
    "https://cdn.jsdelivr.net/gh/nonebot/nonebot2/website/static/plugins.json",
]


class Tag(BaseModel):
    label: str
    color: str


class Plugin(BaseModel):
    module_name: str
    project_link: str
    name: str
    desc: str
    author: str
    homepage: str
    tags: List[Tag]
    is_official: bool


class RepoLicense(BaseModel):
    name: str
    spdx_id: str


class Repo(BaseModel):
    full_name: str
    stargazers_count: int
    open_issues_count: int
    forks_count: int
    archived: bool
    license: RepoLicense


class PyPIPackage(BaseModel):
    description: str
    description_content_type: str
    keywords: str
    version: str
    requires_python: str


if TYPE_CHECKING:

    async def get_plugins() -> List[Plugin]:
        ...

else:

    @cache(ttl=None)
    async def get_plugins() -> List[Plugin]:
        exceptions: List[Exception] = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [executor.submit(httpx.get, url) for url in URLS]

            for future in as_completed(tasks):
                try:
                    resp = future.result()
                    items = resp.json()
                    return [Plugin.parse_obj(item) for item in items]
                except Exception as e:
                    exceptions.append(e)

        raise ModuleLoadFailed("Failed to get plugins list.", exceptions)


def search_plugins(plugins: List[Plugin], query: str) -> List[Plugin]:
    return [
        plugin
        for plugin in plugins
        if any(
            query in value
            for key, value in plugin.dict().items()
            if key in {"name", "module_name", "desc", "project_link"}
        )
    ]


def get_plugin_by_name(name: str, plugins: List[Plugin]) -> Plugin:
    if exact_packages := [
        p for p in plugins if name in {p.name, p.module_name, p.project_link}
    ]:
        return exact_packages[0]
    elif packages := [
        p
        for p in plugins
        if name in p.name or name in p.module_name or name in p.project_link
    ]:
        return packages[0]
    else:
        raise PluginNotFoundError


async def get_github_statistics(repo: str) -> Repo:
    async with httpx.AsyncClient() as client:
        print(repo)
        resp = await client.get(
            f"https://api.github.com/repos/{repo}", follow_redirects=True
        )
        if resp.status_code != httpx.codes.OK:
            raise RuntimeError(f"GitHub API status error: {resp.status_code}")
        return Repo.parse_obj(resp.json())


if TYPE_CHECKING:

    async def get_pypi_meta(package: str) -> PyPIPackage:
        ...

else:

    @cache(ttl=None)
    async def get_pypi_meta(package: str) -> PyPIPackage:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://pypi.org/pypi/{package}/json", follow_redirects=True
            )
            if resp.status_code != httpx.codes.OK:
                raise RuntimeError(
                    f"PyPI JSON API status error: {resp.status_code}"
                )
            return PyPIPackage.parse_obj(resp.json()["info"])
