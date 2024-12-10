# type: ignore
from __future__ import annotations

import os
from typing import Any

# pylint: disable=missing-timeout


class dotdict(dict):
    """dot.notation access to  dictionary attributes"""

    def __getattr__(self, *args):
        value = self.get(*args)
        return dotdict(value) if isinstance(value, dict) else value

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def dget(data: dict, *path: str | list[str], default: Any = None) -> Any:
    """Get element from dict using dot notation.

    Args:
        data (dict): Dictionary to search.
        default (Any, optional): Default value. Defaults to None.

    Returns:
        Any: Element from dict or default value.
    """
    if path is None or not data:
        return default

    ps: list[str] = path if isinstance(path, (list, tuple)) else [path]

    d = None

    for p in ps:
        d = dotget(data, p)

        if d is not None:
            return d

    return d or default


def dotexists(data: dict, *paths: list[str]) -> bool:
    """Check if element exists in dict using dot notation.

    Args:
        data (dict): Dictionary to search.

    Returns:
        bool: True if element exists, False otherwise.
    """
    for path in paths:
        if dotget(data, path, default="@@") != "@@":
            return True
    return False


def dotexpand(path: str) -> list[str]:
    """Expand dot notation path into list of paths. Expands paths with ',' and ':'.

    Args:
        path (str): Path to expand.

    Returns:
        list[str]: List of expanded paths.
    """
    paths = []
    for p in path.replace(' ', '').split(','):
        if not p:
            continue
        if ':' in p:
            paths.extend([p.replace(":", "."), p.replace(":", "_")])
        else:
            paths.append(p)
    return paths


def dotget(data: dict, path: str, default: Any = None) -> Any:
    """Get element from dict using dot notation x.y.z or x_y_z or x:y:z.
    Gets element from dict. Path can be x.y.y or x_y_y or x:y:y.
    if path is x:y:y then element is search using borh x.y.y or x_y_y.

    Args:
        data (dict): The dictionary to search.
        path (str): The path to search.
        default (Any, optional): The default value to return if the path is not found. Defaults to None.

    Returns:
        Any: The element from the dictionary or the default value.
    """

    for key in dotexpand(path):
        d: dict = data
        for attr in key.split('.'):
            d: dict = d.get(attr) if isinstance(d, dict) else None
            if d is None:
                break
        if d is not None:
            return d
    return default


def dotset(data: dict, path: str, value: Any) -> dict:
    """Sets element in dict using dot notation x.y.z or x_y_z or x:y:z"""

    d: dict = data
    attrs: list[str] = path.replace(":", ".").split('.')
    for attr in attrs[:-1]:
        if not attr:
            continue
        d: dict = d.setdefault(attr, {})
    d[attrs[-1]] = value

    return data


def env2dict(prefix: str, data: dict[str, str] | None = None, lower_key: bool = True) -> dict[str, str]:
    """Loads environment variables starting with prefix into."""
    if data is None:
        data = {}
    if not prefix:
        return data
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix.lower()):
            dotset(data, key[len(prefix) + 1 :], value)
    return data
