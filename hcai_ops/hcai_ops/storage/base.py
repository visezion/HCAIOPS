from typing import Any, Dict, List
import abc


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def append(self, stream: str, record: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def read_all(self, stream: str) -> List[Dict[str, Any]]:
        pass
