import argparse
from pathlib import Path

from app.runtime import run


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send scheduled custom messages through desktop WeChat."
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to config JSON file (default: config.json).",
    )
    parser.add_argument(
        "--once",
        metavar="JOB_NAME",
        help="Run a single job immediately and exit.",
    )
    parser.add_argument(
        "--preview",
        metavar="JOB_NAME",
        help="Preview a single job message without sending to WeChat.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        Path(args.config).resolve(),
        once_job_name=args.once,
        preview_job_name=args.preview,
    )
