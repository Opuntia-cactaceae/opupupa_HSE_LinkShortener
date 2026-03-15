import pytest
from datetime import datetime, timezone, timedelta

from src.application.services.time_provider import (
    TimeProvider,
    SystemTimeProvider,
)


class TestTimeProvider:
    def test_time_provider_is_abstract(self):
        
        with pytest.raises(TypeError):
            TimeProvider()  

    def test_system_time_provider_returns_datetime(self):
        
        provider = SystemTimeProvider()
        result = provider.now()
        assert isinstance(result, datetime)

    def test_system_time_provider_returns_timezone_aware(self):
        
        provider = SystemTimeProvider()
        result = provider.now()
        assert result.tzinfo is not None, "Datetime should be timezone-aware"
        assert result.tzinfo == timezone.utc, "Datetime should be in UTC"

    def test_system_time_provider_monotonic_increasing(self):
        
        provider = SystemTimeProvider()
        time1 = provider.now()
        time2 = provider.now()
        time3 = provider.now()
        assert time1 <= time2 <= time3

    def test_system_time_provider_real_time(self):
        
        provider = SystemTimeProvider()
        system_time = datetime.now(timezone.utc)
        provider_time = provider.now()
        
        time_diff = abs((provider_time - system_time).total_seconds())
        assert time_diff < 1.0, f"Time difference too large: {time_diff} seconds"

    def test_system_time_provider_consistent_type(self):
        
        provider = SystemTimeProvider()
        times = [provider.now() for _ in range(10)]
        for t in times:
            assert isinstance(t, datetime)
            assert t.tzinfo == timezone.utc