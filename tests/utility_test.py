import logging
from unittest.mock import Mock, patch

import pytest

from amazon_scraper.utility import retry


class TestRetry:
    def test_retry_success(self):
        mock_func = Mock(return_value="success")
        decorated_func = retry(times=3)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_failure_then_success(self, caplog):
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        decorated_func = retry(times=3)(mock_func)

        with caplog.at_level(logging.WARNING):
            result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 2
        assert f"Exception thrown running {type(mock_func).__name__}, attempt 0 of 3" in caplog.text

    def test_retry_failure_all_attempts(self, caplog):
        mock_func = Mock(side_effect=Exception("fail"))
        decorated_func = retry(times=3, default="default")(mock_func)

        with caplog.at_level(logging.ERROR):
            result = decorated_func()

        assert result == "default"
        assert mock_func.call_count == 3
        assert f"Failed to run {type(mock_func).__name__} after 3 attempts" in caplog.text

    def test_retry_with_sleep(self, caplog):
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        decorated_func = retry(times=3, sleep=1)(mock_func)

        with caplog.at_level(logging.WARNING):
            with patch("time.sleep", return_value=None) as mock_sleep:
                result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 2
        assert mock_sleep.call_count == 1
        assert f"Exception thrown running {type(mock_func).__name__}, attempt 0 of 3" in caplog.text

    def test_retry_raises_exception(self, caplog):
        mock_func = Mock(side_effect=Exception("fail"))
        decorated_func = retry(times=3)(mock_func)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Exception, match="fail"):
                decorated_func()

        assert mock_func.call_count == 3
        assert f"Failed to run {type(mock_func).__name__} after 3 attempts" in caplog.text
