from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib import error, parse, request


@dataclass(frozen=True)
class WechatBotWebhookConfig:
    base_url: str
    token: str
    timeout_seconds: int = 15


class WechatBotWebhookSender:
    def __init__(self, config: WechatBotWebhookConfig) -> None:
        self.config = config

    def send(self, recipient: str, content: str) -> None:
        logger = logging.getLogger(__name__)
        payload = {
            "to": recipient,
            "isRoom": False,
            "data": {
                "type": "text",
                "content": content,
            },
        }
        body = json.dumps(payload).encode("utf-8")

        webhook_url = self.config.base_url.rstrip("/") + "/webhook/msg/v2"
        query = parse.urlencode({"token": self.config.token})
        full_url = f"{webhook_url}?{query}"

        req = request.Request(
            full_url,
            method="POST",
            headers={"Content-Type": "application/json"},
            data=body,
        )

        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except error.URLError as exc:
            raise RuntimeError(f"Wechatbot webhook send failed: {exc}") from exc

        if not raw:
            logger.info("wechatbot_webhook_send recipient=%s", recipient)
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.info("wechatbot_webhook_send recipient=%s", recipient)
            return

        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(
                f"Wechatbot webhook rejected: {data.get('message') or data.get('error', 'unknown error')}"
            )

        logger.info("wechatbot_webhook_send recipient=%s", recipient)
