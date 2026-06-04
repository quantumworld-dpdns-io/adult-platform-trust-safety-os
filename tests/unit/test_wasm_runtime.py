"""Tests for WASMRuntime: load, execute, and sandbox isolation."""

from __future__ import annotations

import os

import pytest

from src.web.wasm_runtime import WASMRuntime


@pytest.fixture
def runtime():
    return WASMRuntime()


def test_load_module_nonexistent(runtime):
    with pytest.raises(FileNotFoundError, match="WASM file not found"):
        runtime.load_module("test", "/nonexistent/path.wasm")


def test_load_module_fallback(runtime, tmp_path):
    wasm_file = tmp_path / "test.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
    result = runtime.load_module("test_mod", str(wasm_file))
    assert result is True


def test_list_modules_empty(runtime):
    assert runtime.list_modules() == []


def test_list_modules_after_load(runtime, tmp_path):
    wasm_file = tmp_path / "mod.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
    runtime.load_module("mod1", str(wasm_file))
    assert "mod1" in runtime.list_modules()


def test_get_module_info(runtime, tmp_path):
    wasm_file = tmp_path / "info.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
    runtime.load_module("info_mod", str(wasm_file))
    info = runtime.get_module_info("info_mod")
    assert info is not None
    assert info["name"] == "info_mod"
    assert info["loaded"] is True


def test_get_module_info_missing(runtime):
    assert runtime.get_module_info("nonexistent") is None


def test_unload_module(runtime, tmp_path):
    wasm_file = tmp_path / "unload.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
    runtime.load_module("unload_mod", str(wasm_file))
    assert "unload_mod" in runtime.list_modules()
    result = runtime.unload_module("unload_mod")
    assert result is True
    assert "unload_mod" not in runtime.list_modules()


def test_unload_nonexistent(runtime):
    result = runtime.unload_module("nonexistent")
    assert result is False


def test_execute_function_not_loaded(runtime):
    with pytest.raises(ValueError, match="Module.*not loaded"):
        runtime.execute_function("nonexistent", "func")


def test_execute_function_returns_none_without_wasmtime(runtime):
    if runtime._wasmtime_available:
        pytest.skip("wasmtime is installed")
    runtime._modules["test"] = {"path": "/fake", "loaded": True}
    result = runtime.execute_function("test", "main")
    assert result is None


def test_get_memory_not_loaded(runtime):
    with pytest.raises(ValueError, match="Module.*not loaded"):
        runtime.get_memory("nonexistent")


def test_set_memory_not_loaded(runtime):
    with pytest.raises(ValueError, match="Module.*not loaded"):
        runtime.set_memory("nonexistent", 0, b"\x00")


def test_sandbox_isolation(runtime, tmp_path):
    wasm_file = tmp_path / "sandbox.wasm"
    wasm_file.write_bytes(b"\x00asm\x01\x00\x00\x00")
    runtime.load_module("sandbox_a", str(wasm_file))
    runtime.load_module("sandbox_b", str(wasm_file))
    assert runtime.list_modules().count("sandbox_a") == 1
    runtime.unload_module("sandbox_a")
    assert "sandbox_a" not in runtime.list_modules()
    assert "sandbox_b" in runtime.list_modules()
