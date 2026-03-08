"""Kafka test fixtures for integration and e2e tests.

Provides mock consumers and producers that capture messages in-memory
instead of connecting to a real Kafka cluster.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, TypeVar
from unittest.mock import AsyncMock

import pytest

from google.protobuf.message import Message

ProtoT = TypeVar("ProtoT", bound=Message)


class MockPyhronProducer:
    """In-memory Kafka producer for testing.

    Captures all messages sent via ``send()`` and stores them
    indexed by topic for later assertion.
    """

    def __init__(self) -> None:
        self.messages: dict[str, list[tuple[str, Message]]] = defaultdict(list)
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def send(
        self,
        topic: str,
        message: Message,
        key: str | None = None,
    ) -> None:
        if not self._started:
            raise RuntimeError("Producer not started")
        self.messages[topic].append((key or "", message))

    def get_messages(self, topic: str) -> list[tuple[str, Message]]:
        return self.messages.get(topic, [])

    def message_count(self, topic: str) -> int:
        return len(self.messages.get(topic, []))

    def clear(self) -> None:
        self.messages.clear()


class MockPyhronConsumer:
    """In-memory Kafka consumer for testing.

    Feed messages via ``enqueue()`` and consume them via ``stream()``.
    """

    def __init__(self, messages: list[Any] | None = None) -> None:
        self._messages = list(messages or [])
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    def enqueue(self, message: Any) -> None:
        self._messages.append(message)

    async def stream(self):
        for msg in self._messages:
            yield msg

    async def commit(self) -> None:
        pass


class MockRedis:
    """In-memory Redis mock for testing.

    Supports basic get/set/lrange/lpush/ltrim/expire/delete operations.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def lpush(self, key: str, *values: str) -> int:
        if key not in self._store:
            self._store[key] = []
        for v in values:
            self._store[key].insert(0, v)
        return len(self._store[key])

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        lst = self._store.get(key, [])
        return lst[start : stop + 1] if lst else []

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        if key in self._store:
            self._store[key] = self._store[key][start : stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        pass  # No-op in mock

    async def close(self) -> None:
        self._store.clear()


# ── Pytest Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_producer() -> MockPyhronProducer:
    """Provide a mock Kafka producer."""
    producer = MockPyhronProducer()
    return producer


@pytest.fixture
def mock_consumer() -> MockPyhronConsumer:
    """Provide a mock Kafka consumer."""
    return MockPyhronConsumer()


@pytest.fixture
def mock_redis() -> MockRedis:
    """Provide a mock Redis client."""
    return MockRedis()
