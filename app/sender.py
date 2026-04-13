from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional
from urllib import error, request


@dataclass
class WeChatSender:
    gateway_url: Optional[str] = None
    gateway_api_key: Optional[str] = None
    
    def send(self, recipient: str, content: str) -> None:
        logger = logging.getLogger(__name__)
        
        if self.gateway_url:
            self._send_via_gateway(recipient, content)
        else:
            self._send_via_wxauto(recipient, content)
    
    def _send_via_gateway(self, recipient: str, content: str) -> None:
        """Send message via local HTTP gateway."""
        logger = logging.getLogger(__name__)
        
        payload = json.dumps({
            "recipient": recipient,
            "content": content,
        }).encode("utf-8")
        
        headers = {"Content-Type": "application/json"}
        if self.gateway_api_key:
            headers["Authorization"] = f"Bearer {self.gateway_api_key}"
        
        req = request.Request(
            f"{self.gateway_url}/send",
            method="POST",
            data=payload,
            headers=headers,
        )
        
        try:
            with request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                if not result.get("success"):
                    raise RuntimeError(f"Gateway error: {result.get('error')}")
                logger.info(f"gateway_send recipient={recipient}")
        except error.URLError as exc:
            raise RuntimeError(f"Failed to reach gateway: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Gateway request failed: {exc}") from exc
    
    def _send_via_wxauto(self, recipient: str, content: str) -> None:
        # Lazy import to keep startup errors focused and allow linting without WeChat runtime.
        try:
            from wxauto import WeChat
        except ImportError as exc:  # pragma: no cover - depends on local Windows environment
            raise RuntimeError(
                "wxauto is not installed. Install dependencies before running the sender."
            ) from exc

        wx = WeChat()
        wx.ChatWith(recipient)
        wx.SendMsg(content)
