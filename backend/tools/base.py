"""
Базовый контракт для всех инструментов.
Каждый инструмент живёт в своём файле и не зависит от других.
"""
from abc import ABC, abstractmethod
from typing import Any


class ToolBase(ABC):
    """Интерфейс одного инструмента (run → dict с success/output)."""

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Уникальный id (латиница, без пробелов), например: anonsms."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Название для отображения в панели."""
        pass

    @property
    def description(self) -> str:
        """Краткое описание (по желанию)."""
        return ""

    @abstractmethod
    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Запуск инструмента. Параметры и результат — словари (JSON-совместимые).

        Контракт результата (поля добавляет/нормализует реестр перед отдачей API):
          - success: bool;
          - output: str — основной текст для UI;
          - error: str — при ошибке (опционально дублируется в output);
          - sections: [{"title": str, "body": str}, ...] — опционально, блоки-карточки;
          - произвольные доп. поля (lookup_meta и т.п.), если клиент их использует.

        Не пробрасывать исключения наружу — возвращать {"success": False, "error": "..."}.
        """
        pass
