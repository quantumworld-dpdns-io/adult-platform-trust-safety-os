"""Event bus: publish-subscribe messaging for decoupled communication."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventSubscription:
    def __init__(
        self,
        subscription_id: str,
        topic: str,
        handler: EventHandler,
        filter_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        self.subscription_id = subscription_id
        self.topic = topic
        self.handler = handler
        self.filter_fn = filter_fn
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.event_count = 0


class EventBus:
    def __init__(self) -> None:
        self._subscriptions: dict[str, EventSubscription] = {}
        self._topic_subscriptions: dict[str, set[str]] = {}
        self._wildcard_subscriptions: set[str] = set()
        self._event_log: list[dict[str, Any]] = []
        self._max_log_size = 10000

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        filter_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> str:
        subscription_id = str(uuid.uuid4())

        sub = EventSubscription(
            subscription_id=subscription_id,
            topic=topic,
            handler=handler,
            filter_fn=filter_fn,
        )
        self._subscriptions[subscription_id] = sub

        if topic == "*":
            self._wildcard_subscriptions.add(subscription_id)
        else:
            if topic not in self._topic_subscriptions:
                self._topic_subscriptions[topic] = set()
            self._topic_subscriptions[topic].add(subscription_id)

        logger.info("event_subscribed", topic=topic, subscription_id=subscription_id)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        sub = self._subscriptions.pop(subscription_id, None)
        if sub is None:
            return False

        if sub.topic == "*":
            self._wildcard_subscriptions.discard(subscription_id)
        elif sub.topic in self._topic_subscriptions:
            self._topic_subscriptions[sub.topic].discard(subscription_id)
            if not self._topic_subscriptions[sub.topic]:
                del self._topic_subscriptions[sub.topic]

        logger.info("event_unsubscribed", subscription_id=subscription_id, topic=sub.topic)
        return True

    async def publish(
        self,
        topic: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        enriched_event = {
            **event,
            "_event_id": event_id,
            "_topic": topic,
            "_timestamp": now,
        }

        subscription_ids = set()
        if topic in self._topic_subscriptions:
            subscription_ids |= self._topic_subscriptions[topic]
        subscription_ids |= self._wildcard_subscriptions

        delivered = 0
        failed = 0
        filtered = 0

        for sub_id in subscription_ids:
            sub = self._subscriptions.get(sub_id)
            if sub is None:
                continue

            if sub.filter_fn and not sub.filter_fn(enriched_event):
                filtered += 1
                continue

            try:
                await sub.handler(enriched_event)
                sub.event_count += 1
                delivered += 1
            except Exception as e:
                logger.error(
                    "event_delivery_failed",
                    subscription_id=sub_id,
                    topic=topic,
                    error=str(e),
                )
                failed += 1

        log_entry = {
            "event_id": event_id,
            "topic": topic,
            "timestamp": now,
            "delivered": delivered,
            "failed": failed,
            "filtered": filtered,
        }
        self._event_log.append(log_entry)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        return {
            "event_id": event_id,
            "topic": topic,
            "delivered": delivered,
            "failed": failed,
            "filtered": filtered,
        }

    def get_subscribers(
        self,
        topic: str | None = None,
    ) -> list[dict[str, Any]]:
        if topic:
            sub_ids = self._topic_subscriptions.get(topic, set()) | {
                sid for sid in self._wildcard_subscriptions
            }
        else:
            sub_ids = set(self._subscriptions.keys())

        return [
            {
                "subscription_id": sub.subscription_id,
                "topic": sub.topic,
                "created_at": sub.created_at,
                "event_count": sub.event_count,
                "has_filter": sub.filter_fn is not None,
            }
            for sub_id in sub_ids
            if (sub := self._subscriptions.get(sub_id)) is not None
        ]

    def get_event_log(
        self,
        topic: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        log = self._event_log
        if topic:
            log = [e for e in log if e["topic"] == topic]
        return log[-limit:]

    def get_stats(self) -> dict[str, Any]:
        topic_counts = {topic: len(sids) for topic, sids in self._topic_subscriptions.items()}
        total_events = sum(sub.event_count for sub in self._subscriptions.values())
        return {
            "total_subscriptions": len(self._subscriptions),
            "total_topics": len(self._topic_subscriptions),
            "wildcard_subscriptions": len(self._wildcard_subscriptions),
            "total_events_published": len(self._event_log),
            "total_events_delivered": total_events,
            "topics": topic_counts,
        }
