import time
from typing import Any, Callable, Tuple, Type, Union

import yaml
from loguru import logger


def retry(
    times: int,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...], None] = Exception,
    sleep: int = 0,
    default: Any = None,
) -> Callable[..., Any]:
    """
    A decorator to retry a function call if it raises an exception. The function will be retried up to `times` times,
    with an optional delay (`sleep`) between retries. If all retries fail, it will either return a default value
    (`default`) or raise the last exception.

    - If `times` is set to 0, the function will not be retried and will immediately return the `default` value if provided.
    - If `exceptions` is set to None, all exceptions will be caught.
    - If `default` is None and all retries fail, the last exception will be raised.

    This decorator is useful for handling temporary issues like network errors or rate limiting. It logs a warning
    message for each retry attempt and an error message if all retries fail.

    Args:
        times (int): The maximum number of retry attempts.
        exceptions (Union[Type[Exception], Tuple[Type[Exception], ...], None], optional): The exceptions to catch. Defaults to Exception.
        sleep (int, optional): The delay (in seconds) between retry attempts. Defaults to 0.
        default (Any, optional): The value to return if all retries fail. Defaults to None.

    Returns:
        Callable[..., Any]: The decorated function.

    Example:
        >>> @retry(times=3, sleep=1)
        ... def my_function():
        ...     raise Exception("Temporary error")
        ...
        >>> my_function()
    """
    if exceptions is None:
        exceptions = (Exception,)
    elif not isinstance(exceptions, tuple):
        exceptions = (exceptions,)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def fx(*args: Any, **kwargs: Any) -> Any:
            if times == 0:
                if default is None:
                    raise RuntimeError("No retries specified and no default value provided.")
                return default

            attempt: int = 0
            for attempt in range(times):
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
