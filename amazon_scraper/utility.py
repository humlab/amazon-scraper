import time
from typing import Any

import yaml
from loguru import logger


def retry(*, times: int, exceptions: Exception | tuple[Exception] = None, sleep: int = 0, default: Any = None) -> Any:
    """Retry a function a number of times if an exception is thrown

    Args:
        times (int): The number of times to retry the function.
        exceptions (Exception | tuple[Exception], optional): The exception or exceptions to catch. Defaults to None.
        sleep (int, optional): The time to sleep between retries. Defaults to 0.
        default (Any, optional): The default value to return if the function fails. Defaults to None.

    Returns:
        Any: The return value of the function.

    Raises:
        Exception: The exception thrown by the function. If the function fails after the number of retries, the exception is raised.
    """
    exceptions = exceptions or (Exception,)

    def decorator(func):
        def fx(*args, **kwargs):
            attempt: int = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:  # pylint: disable=catching-non-exception # type: ignore
                    logger.warning(f'Exception thrown running {func.__name__}, attempt {attempt} of {times}')
                    attempt += 1
                    if attempt == times:
                        logger.error(f'Failed to run {func.__name__} after {times} attempts')
                        if default is None:
                            raise
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
