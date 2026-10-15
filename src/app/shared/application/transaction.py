from typing import Protocol


class TransactionManager(Protocol):
    """Граница транзакции. Интерактор-команда вызывает ``commit()`` в конце.

    Все репозитории в рамках одного HTTP-запроса работают в одной сессии,
    поэтому изменения нескольких модулей (включая обработчики событий)
    коммитятся атомарно. Без ``commit()`` всё откатится при закрытии сессии.
    """

    async def commit(self) -> None: ...

    async def flush(self) -> None: ...
