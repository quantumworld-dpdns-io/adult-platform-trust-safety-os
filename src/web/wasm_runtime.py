import os
from typing import Any, Dict, Optional


class WASMRuntime:
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}
        self._wasmtime_available = False
        try:
            import wasmtime
            self._wasmtime_available = True
            self._wasmtime = wasmtime
        except ImportError:
            pass

    def load_module(self, name: str, wasm_path: str) -> bool:
        if not os.path.exists(wasm_path):
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")
        if not self._wasmtime_available:
            self._modules[name] = {"path": wasm_path, "loaded": True}
            return True
        try:
            engine = self._wasmtime.Engine()
            store = self._wasmtime.Store(engine)
            module = self._wasmtime.Module.from_file(engine, wasm_path)
            self._modules[name] = {
                "engine": engine,
                "store": store,
                "module": module,
                "path": wasm_path,
            }
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to load WASM module: {e}")

    def execute_function(self, module_name: str, function_name: str,
                          args: Optional[list] = None) -> Any:
        if module_name not in self._modules:
            raise ValueError(f"Module '{module_name}' not loaded")
        module_data = self._modules[module_name]
        if not self._wasmtime_available:
            return None
        try:
            store = module_data["store"]
            module = module_data["module"]
            instance = self._wasmtime.Instance(store, module, [])
            func = instance.exports(store)[function_name]
            if args:
                return func(store, *args)
            return func(store)
        except Exception as e:
            raise RuntimeError(f"Failed to execute function: {e}")

    def get_memory(self, module_name: str) -> Optional[bytes]:
        if module_name not in self._modules:
            raise ValueError(f"Module '{module_name}' not loaded")
        if not self._wasmtime_available:
            return None
        try:
            store = self._modules[module_name]["store"]
            module = self._modules[module_name]["module"]
            instance = self._wasmtime.Instance(store, module, [])
            memory = instance.exports(store)["memory"]
            data_ptr = memory.data_ptr(store)
            data_len = memory.data_len(store)
            return bytes(data_ptr[:data_len])
        except Exception:
            return None

    def set_memory(self, module_name: str, offset: int, data: bytes) -> bool:
        if module_name not in self._modules:
            raise ValueError(f"Module '{module_name}' not loaded")
        if not self._wasmtime_available:
            return False
        try:
            store = self._modules[module_name]["store"]
            module = self._modules[module_name]["module"]
            instance = self._wasmtime.Instance(store, module, [])
            memory = instance.exports(store)["memory"]
            data_ptr = memory.data_ptr(store)
            for i, byte in enumerate(data):
                if offset + i < len(data_ptr):
                    data_ptr[offset + i] = byte
            return True
        except Exception:
            return False

    def call_exported_function(self, module_name: str, function_name: str,
                                args: Optional[list] = None) -> Any:
        return self.execute_function(module_name, function_name, args)

    def unload_module(self, module_name: str) -> bool:
        if module_name in self._modules:
            del self._modules[module_name]
            if module_name in self._instances:
                del self._instances[module_name]
            return True
        return False

    def list_modules(self) -> list:
        return list(self._modules.keys())

    def get_module_info(self, module_name: str) -> Optional[Dict]:
        if module_name not in self._modules:
            return None
        data = self._modules[module_name]
        return {
            "name": module_name,
            "path": data.get("path", ""),
            "loaded": True,
        }
