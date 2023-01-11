from typing import TYPE_CHECKING, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from nb_cli import cache
from pydantic import BaseModel
from nb_cli.exceptions import ModuleLoadFailed

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
