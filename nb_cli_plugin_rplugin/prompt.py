from typing import List, Tuple, Callable, Optional

from click import Context
from noneprompt import Choice
from noneprompt import CancelledError
from noneprompt.prompts.list import RT
from nb_cli.cli import CLI_DEFAULT_STYLE
from noneprompt import ListPrompt as _ListPrompt
from noneprompt import InputPrompt as _InputPrompt
from noneprompt import ConfirmPrompt as _ConfirmPrompt
from noneprompt import CheckboxPrompt as _CheckboxPrompt


async def ListPrompt(
    ctx: Context,
    question: str,
    choices: List[Choice[RT]],
    default_select: Optional[int] = None,
) -> Choice[RT]:
    try:
        return await _ListPrompt(
            question, choices=choices, default_select=default_select
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()


async def InputPrompt(
    ctx: Context,
    question: str,
    default_text: Optional[str] = None,
    validator: Optional[Callable[[str], bool]] = None,
) -> str:
    try:
        return await _InputPrompt(
            question, default_text=default_text, validator=validator
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()


async def CheckboxPrompt(
    ctx: Context,
    question: str,
    choices: List[Choice[RT]],
    default_select: Optional[List[int]] = None,
) -> Tuple[Choice[RT], ...]:
    try:
        return await _CheckboxPrompt(
            question, choices=choices, default_select=default_select
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()


async def ConfirmPrompt(
    ctx: Context,
    question: str,
    default_choice: Optional[bool] = None,
) -> bool:
    try:
        return await _ConfirmPrompt(
            question, default_choice=default_choice
        ).prompt_async(style=CLI_DEFAULT_STYLE)
    except CancelledError:
        ctx.exit()
