from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import Any


class KafkaBackboneUnavailable(RuntimeError):
    pass


def _load_kafka_symbols():
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised when kafka is not installed in runtime
        raise KafkaBackboneUnavailable(
            "Kafka support requires the 'kafka-python' package to be installed."
        ) from exc
    return KafkaConsumer, KafkaProducer


@dataclass(frozen=True, slots=True)
class KafkaMessage:
    topic: str
    key: str | None
    value: dict[str, Any]
    partition: int | None = None
    offset: int | None = None
    headers: dict[str, str] | None = None


@dataclass(slots=True)
class KafkaJsonProducer:
    brokers: tuple[str, ...]
    client_id: str
    producer: Any | None = None

    def __post_init__(self) -> None:
        if self.producer is not None:
            return
        _, kafka_producer_cls = _load_kafka_symbols()
        self.producer = kafka_producer_cls(
            bootstrap_servers=list(self.brokers),
            client_id=self.client_id,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value is not None else None,
            linger_ms=20,
        )

    def send(
        self,
        *,
        topic: str,
        value: dict[str, Any],
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        encoded_headers = None
        if headers:
            encoded_headers = [
                (str(header_key), str(header_value).encode("utf-8"))
                for header_key, header_value in headers.items()
            ]
        future = self.producer.send(topic, value=value, key=key, headers=encoded_headers)
        if hasattr(future, "get"):
            future.get(timeout=30)
        if hasattr(self.producer, "flush"):
            self.producer.flush()

    def close(self) -> None:
        if self.producer is not None and hasattr(self.producer, "close"):
            self.producer.close()


@dataclass(slots=True)
class KafkaJsonConsumer:
    brokers: tuple[str, ...]
    group_id: str
    client_id: str
    topics: tuple[str, ...]
    consumer: Any | None = None
    poll_timeout_ms: int = 1000

    def __post_init__(self) -> None:
        if self.consumer is not None:
            return
        kafka_consumer_cls, _ = _load_kafka_symbols()
        self.consumer = kafka_consumer_cls(
            *self.topics,
            bootstrap_servers=list(self.brokers),
            group_id=self.group_id,
            client_id=self.client_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            key_deserializer=lambda value: value.decode("utf-8") if value is not None else None,
        )

    def poll(self) -> list[KafkaMessage]:
        records = self.consumer.poll(timeout_ms=self.poll_timeout_ms)
        messages: list[KafkaMessage] = []
        for _, batch in records.items():
            for record in batch:
                headers: dict[str, str] = {}
                for header_key, header_value in getattr(record, "headers", []) or []:
                    if header_value is None:
                        continue
                    headers[str(header_key)] = header_value.decode("utf-8")
                messages.append(
                    KafkaMessage(
                        topic=record.topic,
                        key=record.key,
                        value=record.value,
                        partition=getattr(record, "partition", None),
                        offset=getattr(record, "offset", None),
                        headers=headers or None,
                    )
                )
        return messages

    def commit(self) -> None:
        if hasattr(self.consumer, "commit"):
            self.consumer.commit()

    def close(self) -> None:
        if self.consumer is not None and hasattr(self.consumer, "close"):
            self.consumer.close()

    @staticmethod
    def topic_names(*, prefix: str, topics: Iterable[str]) -> tuple[str, ...]:
        normalized_prefix = prefix.strip(".")
        resolved: list[str] = []
        for topic in topics:
            clean = topic.strip(".")
            resolved.append(f"{normalized_prefix}.{clean}" if normalized_prefix else clean)
        return tuple(resolved)


__all__ = ["KafkaBackboneUnavailable", "KafkaJsonConsumer", "KafkaJsonProducer", "KafkaMessage"]
