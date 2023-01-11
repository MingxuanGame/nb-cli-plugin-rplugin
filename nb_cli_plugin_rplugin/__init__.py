import locale
import gettext
from pathlib import Path

t = gettext.translation(
    "nb-cli-plugin-rplugin",
    localedir=Path(__file__).parent / "locale",
    languages=[lang] if (lang := locale.getlocale()[0]) else None,
    fallback=True,
)
_ = t.gettext
