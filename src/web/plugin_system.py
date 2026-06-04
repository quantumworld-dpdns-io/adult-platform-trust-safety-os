import importlib
import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Optional


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Dict] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._plugin_dir = os.path.join(os.getcwd(), "plugins")
        os.makedirs(self._plugin_dir, exist_ok=True)

    def load_plugin(self, plugin_path: str, plugin_name: Optional[str] = None) -> bool:
        if not os.path.exists(plugin_path):
            raise FileNotFoundError(f"Plugin file not found: {plugin_path}")
        if plugin_name is None:
            plugin_name = os.path.splitext(os.path.basename(plugin_path))[0]
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load plugin spec: {plugin_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            plugin_info = {
                "name": plugin_name,
                "path": plugin_path,
                "module": module,
                "loaded": True,
                "hooks": {},
            }
            if hasattr(module, "PLUGIN_INFO"):
                plugin_info.update(module.PLUGIN_INFO)
            self._plugins[plugin_name] = plugin_info
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to load plugin: {e}")

    def unload_plugin(self, plugin_name: str) -> bool:
        if plugin_name not in self._plugins:
            return False
        plugin = self._plugins[plugin_name]
        for hook_name in plugin.get("hooks", {}).keys():
            if hook_name in self._hooks:
                self._hooks[hook_name] = [
                    h for h in self._hooks[hook_name]
                    if not hasattr(h, "__plugin__") or h.__plugin__ != plugin_name
                ]
        if plugin_name in sys.modules:
            del sys.modules[plugin_name]
        del self._plugins[plugin_name]
        return True

    def list_plugins(self) -> List[Dict]:
        return [
            {"name": name, "loaded": info.get("loaded", False)}
            for name, info in self._plugins.items()
        ]

    def execute_plugin(self, plugin_name: str, function_name: str,
                        *args, **kwargs) -> Any:
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not loaded")
        module = self._plugins[plugin_name]["module"]
        if not hasattr(module, function_name):
            raise AttributeError(f"Function '{function_name}' not found in plugin")
        func = getattr(module, function_name)
        return func(*args, **kwargs)

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        if plugin_name not in self._plugins:
            return None
        plugin = self._plugins[plugin_name]
        return {
            "name": plugin.get("name"),
            "path": plugin.get("path"),
            "loaded": plugin.get("loaded"),
            "hooks": list(plugin.get("hooks", {}).keys()),
        }

    def register_hook(self, hook_name: str, callback: Callable,
                       plugin_name: Optional[str] = None) -> None:
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        if plugin_name:
            callback.__plugin__ = plugin_name
        self._hooks[hook_name].append(callback)

    def execute_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        if hook_name not in self._hooks:
            return []
        results = []
        for callback in self._hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        return results

    def discover_plugins(self, directory: Optional[str] = None) -> List[str]:
        plugin_dir = directory or self._plugin_dir
        if not os.path.exists(plugin_dir):
            return []
        plugins = []
        for filename in os.listdir(plugin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                plugins.append(os.path.join(plugin_dir, filename))
        return plugins
