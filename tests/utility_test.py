import logging
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from amazon_scraper.utility import load_yaml, retry


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

    def test_retry_with_custom_exception(self, caplog):
        class CustomException(Exception):
            pass

        mock_func = Mock(side_effect=[CustomException("custom fail"), "success"])
        decorated_func = retry(times=3, exceptions=CustomException)(mock_func)

        with caplog.at_level(logging.WARNING):
            result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 2
        assert f"Exception thrown running {type(mock_func).__name__}, attempt 0 of 3" in caplog.text

    def test_retry_with_multiple_exceptions(self, caplog):
        class CustomException1(Exception):
            pass

        class CustomException2(Exception):
            pass

        mock_func = Mock(side_effect=[CustomException1("fail1"), CustomException2("fail2"), "success"])
        decorated_func = retry(times=3, exceptions=(CustomException1, CustomException2))(mock_func)

        with caplog.at_level(logging.WARNING):
            result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 3
        assert f"Exception thrown running {type(mock_func).__name__}, attempt 0 of 3" in caplog.text

    def test_retry_with_no_exceptions(self):
        mock_func = Mock(return_value="success")
        decorated_func = retry(times=3, exceptions=None)(mock_func)

        result = decorated_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_with_zero_attempts(self):
        mock_func = Mock(side_effect=Exception("fail"))
        decorated_func = retry(times=0)(mock_func)

        with pytest.raises(RuntimeError, match="No retries specified and no default value provided."):
            decorated_func()

        assert mock_func.call_count == 0

    def test_retry_with_zero_attempts_and_default(self):
        mock_func = Mock(side_effect=Exception("fail"))
        decorated_func = retry(times=0, default="default_value")(mock_func)

        result = decorated_func()

        assert result == "default_value"
        assert mock_func.call_count == 0

    def test_retry_with_default_return_on_failure(self):
        mock_func = Mock(side_effect=Exception("fail"))
        decorated_func = retry(times=3, default="default_value")(mock_func)

        result = decorated_func()

        assert result == "default_value"
        assert mock_func.call_count == 3

    def test_retry_fx_function_name_logging(self, caplog):
        def sample_function():
            raise ValueError("Test exception")

        decorated_func = retry(times=3)(sample_function)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError, match="Test exception"):
                decorated_func()

        assert "Exception thrown running sample_function, attempt 0 of 3" in caplog.text
        assert "Failed to run sample_function after 3 attempts" in caplog.text

    def test_retry_fx_class_method_logging(self, caplog):
        class SampleClass:
            def sample_method(self):
                raise ValueError("Test exception")

        sample_instance = SampleClass()
        decorated_func = retry(times=3)(sample_instance.sample_method)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError, match="Test exception"):
                decorated_func()

        assert "Exception thrown running sample_method, attempt 0 of 3" in caplog.text
        assert "Failed to run sample_method after 3 attempts" in caplog.text


class TestLoadYaml:
    def test_load_yaml_full_document(self):
        yaml_content = """
        key1: value1
        key2:
            subkey1: subvalue1
            subkey2: subvalue2
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as temp_file:
            temp_file.write(yaml_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:

            result = load_yaml(temp_file_path)
            assert result == {
                "key1": "value1",
                "key2": {"subkey1": "subvalue1", "subkey2": "subvalue2"},
            }
        finally:
            os.remove(temp_file_path)

    def test_load_yaml_subset_single_key(self):
        yaml_content = """
        key1: value1
        key2:
            subkey1: subvalue1
            subkey2: subvalue2
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as temp_file:
            temp_file.write(yaml_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:

            result = load_yaml(temp_file_path, subset="key2")
            assert result == {"subkey1": "subvalue1", "subkey2": "subvalue2"}
        finally:
            os.remove(temp_file_path)

    def test_load_yaml_subset_nested_keys(self):
        yaml_content = """
        key1: value1
        key2:
            subkey1: subvalue1
            subkey2: subvalue2
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as temp_file:
            temp_file.write(yaml_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:

            result = load_yaml(temp_file_path, subset=["key2", "subkey1"])
            assert result == "subvalue1"
        finally:
            os.remove(temp_file_path)

    def test_load_yaml_subset_key_not_found(self):
        yaml_content = """
        key1: value1
        key2:
            subkey1: subvalue1
            subkey2: subvalue2
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as temp_file:
            temp_file.write(yaml_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:

            result = load_yaml(temp_file_path, subset=["key2", "nonexistent"])
            assert result is None
        finally:
            os.remove(temp_file_path)

    def test_load_yaml_empty_document(self):
        yaml_content = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as temp_file:
            temp_file.write(yaml_content.encode("utf-8"))
            temp_file_path = temp_file.name

        try:

            result = load_yaml(temp_file_path)
            assert result is None
        finally:
            os.remove(temp_file_path)
