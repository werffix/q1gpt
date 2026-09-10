import html
import re
from dataclasses import dataclass


@dataclass(slots=True)
class FormattedAnswer:
    text: str
    parse_mode: str | None = "HTML"
    rich: bool = False


def markdown_to_html(markdown: str) -> str:
    """Convert common LLM Markdown constructs into Telegram-safe HTML."""
    fenced: list[str] = []

    def fence(match: re.Match[str]) -> str:
        language = html.escape(match.group(1) or "")
        code = html.escape(match.group(2).strip("\n"))
        fenced.append(f'<pre><code class="language-{language}">{code}</code></pre>' if language else f"<pre>{code}</pre>")
        return f"\x00CODE{len(fenced)-1}\x00"

    text = re.sub(r"```([\w+-]*)\n?(.*?)```", fence, markdown, flags=re.DOTALL)
    text = html.escape(text, quote=False)
    text = re.sub(r"^###### (.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,5} (.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<b>{m.group(1) or m.group(2)}</b>", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)", lambda m: f"<i>{m.group(1) or m.group(2)}</i>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    text = re.sub(r"^> ?(.+)$", r"<blockquote>\1</blockquote>", text, flags=re.MULTILINE)
    for i, block in enumerate(fenced):
        text = text.replace(f"\x00CODE{i}\x00", block)
    return text


def format_answer(markdown: str) -> FormattedAnswer:
    rich = bool(re.search(r"^#{1,6} |\|.*\|\s*$|^> ", markdown, re.MULTILINE))
    return FormattedAnswer(markdown_to_html(markdown), "HTML", rich)
