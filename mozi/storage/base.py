"""Base storage classes for Mozi.

This module provides abstract base classes for storage implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BaseStore(ABC, Generic[T]):
    """Abstract base class for all stores.

    This class defines the common interface that all store implementations
    must follow. Stores handle persistence for different entity types.

    Attributes
    ----------
    db_path : str
        Path to the SQLite database file.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize the store.

        Parameters
        ----------
        db_path : str
            Path to the SQLite database file.
        """
        self.db_path = db_path

    @abstractmethod
    async def get(self, id: str) -> T | None:
        """Get an entity by ID.

        Parameters
        ----------
        id : str
            The unique identifier of the entity.

        Returns
        -------
        T | None
            The entity if found, None otherwise.
        """
        pass

    @abstractmethod
    async def list(
        self,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[T]:
        """List entities with optional filtering.

        Parameters
        ----------
        limit : int
            Maximum number of entities to return.
        **kwargs : Any
            Additional filter parameters.

        Returns
        -------
        list[T]
            List of matching entities.
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID.

        Parameters
        ----------
        id : str
            The unique identifier of the entity.

        Returns
        -------
        bool
            True if the entity was deleted, False if not found.
        """
        pass
