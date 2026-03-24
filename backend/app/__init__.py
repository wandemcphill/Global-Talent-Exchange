from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys


sys.modules.setdefault("app", sys.modules[__name__])


class _BackendAppAliasLoader(importlib.abc.Loader):
    def __init__(self, alias_name: str, target_name: str) -> None:
        self.alias_name = alias_name
        self.target_name = target_name

    def create_module(self, spec):
        module = importlib.import_module(self.target_name)
        sys.modules[self.alias_name] = module
        return module

    def exec_module(self, module) -> None:
        return None

    def get_code(self, fullname: str):
        target_spec = importlib.util.find_spec(self.target_name)
        if target_spec is None or target_spec.loader is None:
            return None
        get_code = getattr(target_spec.loader, "get_code", None)
        if get_code is None:
            return None
        return get_code(self.target_name)

    def get_source(self, fullname: str):
        target_spec = importlib.util.find_spec(self.target_name)
        if target_spec is None or target_spec.loader is None:
            return None
        get_source = getattr(target_spec.loader, "get_source", None)
        if get_source is None:
            return None
        return get_source(self.target_name)


class _BackendAppAliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        if not fullname.startswith("backend.app."):
            return None
        target_name = f"app{fullname[len('backend.app'):]}"
        target_spec = importlib.util.find_spec(target_name)
        if target_spec is None:
            return None
        is_package = target_spec.submodule_search_locations is not None
        return importlib.util.spec_from_loader(
            fullname,
            _BackendAppAliasLoader(fullname, target_name),
            is_package=is_package,
        )


if not any(isinstance(finder, _BackendAppAliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _BackendAppAliasFinder())


def __getattr__(name: str):
    if name in {"app", "create_app"}:
        from .main import app, create_app

        return {"app": app, "create_app": create_app}[name]
    raise AttributeError(name)


__all__ = ["app", "create_app"]
