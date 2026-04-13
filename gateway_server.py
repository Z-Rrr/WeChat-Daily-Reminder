"""
Local WeChat gateway server.
Wraps wxauto in a Flask HTTP service.
Runs on local Windows machine; cloud instances call this to send messages.
"""

import argparse
import json
import logging
from pathlib import Path

from flask import Flask, request, jsonify


app = Flask(__name__)

# Simple API key for basic auth
GATEWAY_API_KEY = None


def _setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    file_handler = logging.FileHandler(
        log_dir / "gateway.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)


def _require_api_key():
    """Middleware to check API key."""
    if GATEWAY_API_KEY is None:
        return None
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return "Missing or invalid Authorization header"
    
    token = auth_header[7:]
    if token != GATEWAY_API_KEY:
        return "Invalid API key"
    
    return None


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/send", methods=["POST"])
def send_message():
    """
    Send a message via WeChat.
    
    Request JSON:
    {
        "recipient": "好友名称或群名",
        "content": "消息内容"
    }
    
    Response JSON:
    {
        "success": true,
        "message": "Message sent successfully"
    }
    """
    auth_error = _require_api_key()
    if auth_error:
        return jsonify({"success": False, "error": auth_error}), 401
    
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body must be JSON"}), 400
        
        recipient = data.get("recipient", "").strip()
        content = data.get("content", "").strip()
        
        if not recipient:
            return jsonify({"success": False, "error": "recipient is required"}), 400
        if not content:
            return jsonify({"success": False, "error": "content is required"}), 400
        
        logger.info(f"gateway_send_start recipient={recipient}")
        
        try:
            from wxauto import WeChat
        except ImportError:
            logger.error("wxauto not installed")
            return jsonify({
                "success": False,
                "error": "wxauto not available; is WeChat running?"
            }), 503
        
        wx = WeChat()
        wx.ChatWith(recipient)
        wx.SendMsg(content)
        
        logger.info(f"gateway_send_success recipient={recipient}")
        return jsonify({"success": True, "message": "Message sent successfully"}), 200
        
    except Exception as exc:
        logger.exception(f"gateway_send_error recipient={data.get('recipient')}")
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


def main():
    global GATEWAY_API_KEY
    
    parser = argparse.ArgumentParser(
        description="Local WeChat gateway server"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to listen on (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication (optional; if omitted, no auth required)",
    )
    
    args = parser.parse_args()
    GATEWAY_API_KEY = args.api_key
    
    _setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting WeChat gateway server on {args.host}:{args.port}")
    if GATEWAY_API_KEY:
        logger.info(f"API key authentication enabled")
    else:
        logger.warning("API key authentication disabled; server is open to all requests")
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
