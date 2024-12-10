# type: ignore
from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass, field, fields
from inspect import isclass
from typing import Any, Callable, Generic, Self, Type, TypeVar

from .config import Config
from .utility import dget

T = TypeVar("T", str, int, float)


@dataclass
class Configurable:
    """A decorator for dataclassed classes that will resolve all ConfigValue fields"""

    def resolve(self):
        """Resolve all ConfigValue fields in the dataclass."""
        for attrib in fields(self):
            if isinstance(getattr(self, attrib.name), ConfigValue):
                setattr(self, attrib.name, getattr(self, attrib.name).resolve())

    # def __post_init__(self):
    #     self.resolve()


@dataclass
class ConfigValue(Generic[T]):
    """A class to represent a value that should be resolved from a configuration file"""

    key: str | Type[T]
    default: T | None = None
    description: str | None = None
    after: Callable[[T], T] | None = None
    mandatory: bool = False

    @property
    def value(self) -> T:
        """Resolve the value from the current store (configuration file)"""
        return self.resolve()

    def resolve(self) -> T:
        """Resolve the value from the current store (configuration file)"""
        if isinstance(self.key, Config):
            return ConfigStore.config()  # type: ignore
        if isclass(self.key):
            return self.key()
        if self.mandatory and not self.default:
            if not ConfigStore.config().exists(self.key):
                raise ValueError(f"ConfigValue {self.key} is mandatory but missing from config")

        value = ConfigStore.config().get(*self.key.split(","), default=self.default)
        if value and self.after:
            return self.after(value)
        return value

    @staticmethod
    def create_field(key: str, default: Any = None, description: str = None) -> Any:
        """Create a field for a dataclass that will be resolved from the configuration file"""
        return field(  # pylint: disable=invalid-field-call
            default_factory=lambda: ConfigValue(key=key, default=default, description=description).resolve()
        )


class ConfigStore:
    """A class to manage configuration files and contexts"""

    store: dict[str, str | Config] = {"default": None}
    context: str = "default"

    @classmethod
    def config(cls) -> "Config":
        """Get the current configuration object

        Raises:
            ValueError: If the configuration object is not properly initialized

        Returns:
            Config: The configuration object
        """
        if not isinstance(cls.store.get(cls.context), Config):
            raise ValueError(f"Config context {cls.context} not properly initialized")
        return cls.store.get(cls.context)

    @classmethod
    def resolve(cls, value: T | ConfigValue) -> T:
        """Resolve a ConfigValue object

        Args:
            value (T | ConfigValue): The value to resolve

        Returns:
            T: The resolved value
        """
        if not isinstance(value, ConfigValue):
            return value
        return dget(cls.config(), value.key)

    @classmethod
    def configure_context(
        cls,
        *,
        context: str = "default",
        source: Config | str | dict = None,
        env_filename: str | None = None,
        env_prefix: str = None,
    ) -> Self:
        """Configure a context with a configuration file

        Args:
            context (str, optional): The context to configure. Defaults to "default".
            source (Config | str | dict, optional): The configuration source. Defaults to None.
            env_filename (str | None, optional): Environment filename. Defaults to None.
            env_prefix (str, optional): Environment prefix. Defaults to None.

        Raises:
            ValueError: If the context is not defined and no source is provided

        Returns:
            Self: The ConfigStore object
        """
        if not cls.store.get(context) and not source:
            raise ValueError(f"Config context {context} undefined, cannot initialize")

        if isinstance(source, Config):
            return cls._set_config(context=context, cfg=source)

        if not source and isinstance(cls.store.get(context), Config):
            return cls.store.get(context)

        cfg: Config = Config.load(
            source=source or cls.store.get(context),
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
        )

        return cls._set_config(context=context, cfg=cfg)

    @classmethod
    def _set_config(cls, *, context: str = "default", cfg: Config | None = None) -> Self:
        """Set the configuration object for a context

        Args:
            context (str, optional): The context to set. Defaults to "default".
            cfg (Config | None, optional): The configuration object. Defaults to None.

        Raises:
            ValueError: If the configuration object is not a Config object

        Returns:
            Self: The ConfigStore object
        """
        if not isinstance(cfg, Config):
            raise ValueError(f"Expected Config, found {type(cfg)}")
        cfg.context = context
        cls.store[context] = cfg
        cls.context = context
        return cls.store[context]


configure_context = ConfigStore.configure_context


def resolve_arguments(fn_or_cls, args, kwargs):
    """Resolve any ConfigValue arguments in a function or class constructor"""
    kwargs = {
        k: v.default
        for k, v in inspect.signature(fn_or_cls).parameters.items()
        if isinstance(v.default, ConfigValue) and v.default is not inspect.Parameter.empty
    } | kwargs
    args = (a.resolve() if isinstance(a, ConfigValue) else a for a in args)
    for k, v in kwargs.items():
        if isinstance(v, ConfigValue):
            kwargs[k] = v.resolve()
    return args, kwargs


def inject_config(fn_or_cls: T) -> Callable[..., T]:
    """Inject configuration values into a function or class constructor

    Args:
        fn_or_cls (T): The function or class constructor

    Returns:
        Callable[..., T]: The decorated function or class constructor
    """

    @functools.wraps(fn_or_cls)
    def decorated(*args, **kwargs):
        args, kwargs = resolve_arguments(fn_or_cls, args, kwargs)
        return fn_or_cls(*args, **kwargs)

    return decorated
