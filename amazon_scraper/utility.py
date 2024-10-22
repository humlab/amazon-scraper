import time
from typing import Any

import yaml
from loguru import logger


def retry(
    times: int, exceptions: type[Exception] | tuple[type[Exception]] = Exception, sleep: int = 0, default: Any = None
) -> Any:
    """
    Retry decorator to retry a function call if it raises an exception.

    Args:
        times (int): Number of times to retry.
        exceptions (Exception | tuple[Exception], optional): Exception(s) to catch. Defaults to None.
        sleep (int, optional): Time to sleep between retries. Defaults to 0.
        default (Any, optional): Default value to return if all retries fail. Defaults to None.

    Returns:
        Any: The result of the function call or the default value if it fails.
    """
    exceptions = exceptions or (Exception,)

    def decorator(func: Any) -> Any:
        def fx(*args: Any, **kwargs: Any) -> Any:
            attempt: int = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:  # pylint: disable=catching-non-exception, broad-exception-caught # type: ignore
                    logger.warning(f'Exception thrown running {func.__name__}, attempt {attempt} of {times}')
                    attempt += 1
                    if attempt == times:
                        logger.error(f'Failed to run {func.__name__} after {times} attempts')
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
