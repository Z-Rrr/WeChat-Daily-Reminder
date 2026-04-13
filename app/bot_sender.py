from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class WebhookBotConfig:
    webhook_url: str
    api_key: str | None = None
    timeout_seconds: int = 15


class WebhookBotSender:
    def __init__(self, config: WebhookBotConfig) -> None:
        self.config = config

    def send(self, recipient: str, content: str) -> None:
        payload = {
            "recipient": recipient,
            "content": content,
        }
        body = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        req = request.Request(
            self.config.webhook_url,
            method="POST",
            headers=headers,
            data=body,
        )

        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except error.URLError as exc:
            raise RuntimeError(f"Webhook send failed: {exc}") from exc

        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(f"Webhook send rejected: {data.get('error', 'unknown error')}")
