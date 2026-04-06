from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WeChatSender:
    def send(self, recipient: str, content: str) -> None:
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
