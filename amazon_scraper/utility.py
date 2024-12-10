import time
from typing import Any, Callable, Tuple, Type, Union

import yaml
from loguru import logger


def retry(
    times: int,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    sleep: int = 0,
    default: Any = None,
) -> Callable[..., Any]:
    """
    Retry decorator to retry a function call if it raises an exception.

    Args:
        times (int): Number of times to retry.
        exceptions (Union[Type[Exception], Tuple[Type[Exception], ...]], optional): Exceptions to catch. Defaults to Exception.
        sleep (int, optional): Time to sleep between retries. Defaults to 0.
        default (Any, optional): Default value to return if all retries fail. Defaults to None.

    Returns:
        Callable[..., Any]: The decorated function.

    Example:
        >>> @retry(times=3)
        ... def my_function():
        ...     raise Exception
        ...
        >>> my_function()
    """
    if exceptions is None:
        exceptions = (Exception,)
    elif not isinstance(exceptions, tuple):
        exceptions = (exceptions,)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def fx(*args: Any, **kwargs: Any) -> Any:
            attempt: int = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:  # pylint: disable=broad-exception-caught, catching-non-exception
                    if hasattr(func, '__name__'):
                        func_name = func.__name__
                    else:
                        func_name = type(func).__name__

                    logger.warning(f'Exception thrown running {func_name}, attempt {attempt} of {times}')
                    attempt += 1
                    if attempt == times:
                        logger.error(f'Failed to run {func_name} after {times} attempts')
                        if default is None:
                            raise
                        return default
                    if sleep:
                        time.sleep(sleep)
            return default

        return fx

    return decorator


def load_yaml(document: str, subset: str | list[str] | None = None) -> Any:
    """Get data from a YAML file. Optionally, get a subset of the data. Subset is a string or a list of keys.

    Args:
        document (str): Document path.
        subset (str or list, optional): String or list of keys. Defaults to None.

    Returns:
        Any: Data from the YAML file.
    """
    with open(document, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if subset is not None:
            if isinstance(subset, str):
                subset = [subset]
            for key in subset:
                data = data.get(key)
                if data is None:
                    break
            return data
        return data
