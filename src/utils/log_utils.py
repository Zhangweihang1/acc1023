from __future__ import annotations

from datetime import datetime
from pathlib import Path


def append_text_log(log_path: Path, message_text: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(f"[{timestamp_text}] {message_text}\n")

