"""Tests for CircuitBreaker: CLOSED, OPEN, HALF_OPEN states."""

from __future__ import annotations

import asyncio

import pytest

from src.utils.circuit_breaker import CircuitBreaker, State


@pytest.fixture
def breaker():
    return CircuitBreaker(failure_threshold=3, recovery_timeout=0.1, half_open_max_calls=1)


async def test_closed_state(breaker):
    assert breaker.state is State.CLOSED


async def test_call_passes_through_closed(breaker):
    async def success():
        return 42
    result = await breaker.call(success)
    assert result == 42
    assert breaker.state is State.CLOSED


async def test_failure_increments_count(breaker):
    async def fail():
        raise ValueError("boom")
    with pytest.raises(ValueError):
        await breaker.call(fail)
    assert breaker._failure_count == 1
    assert breaker.state is State.CLOSED


async def test_open_state(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    assert breaker.state is State.OPEN


async def test_open_rejects_calls(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    async def ok():
        return "ok"
    with pytest.raises(CircuitBreaker.CircuitOpenError):
        await breaker.call(ok)


async def test_half_open_after_recovery(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    assert breaker.state is State.OPEN
    await asyncio.sleep(0.15)
    state = await breaker.get_state()
    assert state is State.HALF_OPEN


async def test_half_open_success_closes(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    await asyncio.sleep(0.15)
    async def ok():
        return "recovered"
    result = await breaker.call(ok)
    assert result == "recovered"
    assert breaker.state is State.CLOSED


async def test_half_open_failure_reopens(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    await asyncio.sleep(0.15)
    with pytest.raises(ValueError):
        await breaker.call(fail)
    assert breaker.state is State.OPEN


async def test_record_success(breaker):
    await breaker.record_success()
    assert breaker.state is State.CLOSED
    assert breaker._failure_count == 0


async def test_manual_reset(breaker):
    async def fail():
        raise ValueError("boom")
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(fail)
    assert breaker.state is State.OPEN
    await breaker.reset()
    assert breaker.state is State.CLOSED
    assert breaker._failure_count == 0


async def test_get_state_async(breaker):
    state = await breaker.get_state()
    assert state is State.CLOSED


async def test_failure_count_threshold():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    async def fail():
        raise RuntimeError("err")
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    assert cb.state is State.CLOSED
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    assert cb.state is State.OPEN
