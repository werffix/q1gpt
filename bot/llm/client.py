import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from bot.config import get_settings

logger = logging.getLogger("llm_api")


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Small Responses API client with streaming and retry support."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.timeout = settings.llm_timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def respond(self, model: str, messages: list[dict], image_urls: list[str] | None = None, stream: bool = True) -> AsyncIterator[str]:
        content_messages = messages
        if image_urls and content_messages:
            last = content_messages[-1]
            text = last.get("content", "")
            last = {**last, "content": [{"type": "input_text", "text": text}, *[{"type": "input_image", "image_url": url} for url in image_urls]]}
            content_messages = [*content_messages[:-1], last]
        payload = {"model": model, "input": content_messages, "stream": stream}
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if stream:
                        async with client.stream("POST", f"{self.base_url}/responses", headers=self._headers(), json=payload) as response:
                            if response.is_error:
                                raise LLMError(await self._error_text(response))
                            async for line in response.aiter_lines():
                                if not line.startswith("data:"):
                                    continue
                                data = line[5:].strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    event = json.loads(data)
                                except json.JSONDecodeError:
                                    continue
                                text = event.get("delta") or event.get("text") or event.get("output_text")
                                if text:
                                    yield str(text)
                    else:
                        response = await client.post(f"{self.base_url}/responses", headers=self._headers(), json=payload)
                        if response.is_error:
                            raise LLMError(await self._error_text(response))
                        data = response.json()
                        yield str(data.get("output_text") or data.get("output", ""))
                return
            except (httpx.HTTPError, LLMError) as exc:
                logger.exception("LLM request failed (attempt %s)", attempt + 1)
                if attempt == 1:
                    raise LLMError("Сервис модели временно недоступен. Попробуйте ещё раз позже.") from exc
                await asyncio.sleep(0.8 * (attempt + 1))

    async def _error_text(self, response: httpx.Response) -> str:
        try:
            detail = response.json().get("error", {}).get("message")
            if detail:
                return str(detail)
        except (ValueError, TypeError):
            pass
        return f"HTTP {response.status_code}"

    async def generate_image(self, model: str, prompt: str, image_urls: list[str] | None = None) -> bytes | str:
        payload = {"model": model, "prompt": prompt}
        if image_urls:
            payload["image_urls"] = image_urls
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/images/generations", headers=self._headers(), json=payload)
                    if response.is_error:
                        raise LLMError(await self._error_text(response))
                    data = response.json()
                    item = (data.get("data") or [{}])[0]
                    if item.get("b64_json"):
                        import base64
                        return base64.b64decode(item["b64_json"])
                    if item.get("url"):
                        return str(item["url"])
                    raise LLMError("Модель не вернула изображение.")
            except (httpx.HTTPError, LLMError) as exc:
                logger.exception("Image request failed (attempt %s)", attempt + 1)
                if attempt == 1:
                    raise LLMError("Не удалось сгенерировать изображение.") from exc
                await asyncio.sleep(0.8 * (attempt + 1))
