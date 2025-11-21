import json
import os
from typing import Any, Dict, List

from .base import StorageBackend


class FileSystemStorage(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _path(self, stream: str) -> str:
        return os.path.join(self.base_path, f"{stream}.jsonl")

    def append(self, stream: str, record: Dict[str, Any]) -> None:
        path = self._path(stream)
        with open(path, "a", encoding="utf8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self, stream: str) -> List[Dict[str, Any]]:
        path = self._path(stream)
        if not os.path.exists(path):
            return []
        out: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
