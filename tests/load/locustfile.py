"""
Load testing with Locust for LinkShortener API.

Scenarios:
1. Massive link creation - POST /links/shorten
2. Heavy redirect traffic - GET /opupupa/{short_code}
3. Cache efficiency - compare cold cache vs warm cache

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Configuration:
    - Set host via command line or environment variable LOCUST_HOST
    - Number of users and spawn rate can be configured via UI or command line
"""
import random
import string
from datetime import datetime, timezone, timedelta
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# Global pool of short codes for redirect tests (populated in on_test_start)
SHORT_CODES_POOL = []
MIN_POOL_SIZE = 10  # Minimum number of short codes to ensure tests can run

def generate_random_url():
    """Generate a random URL for testing."""
    domain = ''.join(random.choices(string.ascii_lowercase, k=10))
    path = ''.join(random.choices(string.ascii_lowercase, k=5))
    return f"https://{domain}.example.com/{path}"


def generate_random_alias():
    """Generate a random short alias for custom_alias."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


class LinkCreationUser(HttpUser):
    """Simulate users creating short links."""
    wait_time = between(1, 3)  # wait 1-3 seconds between tasks

    @task(3)
    def create_link_with_random_alias(self):
        """Create a short link with random custom alias."""
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                # Store the short_code for redirect users (if we had shared state)
                # In distributed mode, we can't easily share across workers
            elif response.status_code == 409:
                # Alias already exists - treat as success (realistic scenario)
                response.success()
            elif response.status_code == 429:
                # Rate limit reached - expected, treat as success
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def create_link_without_alias(self):
        """Create a short link without custom alias (system generates)."""
        payload = {
            "original_url": generate_random_url(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 409:
                # Alias collision unlikely without custom alias, but treat as success
                response.success()
            elif response.status_code == 429:
                # Rate limit reached - expected, treat as success
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class RedirectUser(HttpUser):
    """Simulate users redirecting through short links."""
    wait_time = between(0.5, 2)  # faster wait time for redirects

    @task(10)
    def redirect_to_short_link(self):
        """Redirect to a random short link from the prepopulated pool."""
        if not SHORT_CODES_POOL:
            # No short codes available, skip this request
            return

        short_code = random.choice(SHORT_CODES_POOL)
        # Don't follow redirects to avoid extra load on target URLs
        self.client.get(f"/opupupa/{short_code}", allow_redirects=False)

    @task(1)
    def create_link(self):
        """Occasionally create a new link (low frequency)."""
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                # Optionally add the new short code to the pool for future redirects
                short_code = response.json()["short_code"]
                SHORT_CODES_POOL.append(short_code)
            elif response.status_code == 409:
                # Alias already exists - treat as success (realistic scenario)
                response.success()
            elif response.status_code == 429:
                # Rate limit reached - expected, treat as success
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class CacheEfficiencyUser(HttpUser):
    """
    Test cache efficiency by comparing cold vs warm cache performance.

    This user should be run in two phases:
    1. Cold cache: after cache flush
    2. Warm cache: after cache is populated
    """
    wait_time = between(0.1, 0.5)  # very fast to generate high load

    @task(8)
    def redirect_cached(self):
        """Redirect to a short link (likely cache hit after first request)."""
        if not SHORT_CODES_POOL:
            # No short codes available, skip this request
            return

        short_code = random.choice(SHORT_CODES_POOL)
        self.client.get(f"/opupupa/{short_code}", allow_redirects=False)

    @task(2)
    def redirect_uncached(self):
        """Redirect to a new short link (cache miss)."""
        # Create a new link and immediately redirect to it (cache miss)
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                short_code = response.json()["short_code"]
                # Add to pool for future cached redirects
                SHORT_CODES_POOL.append(short_code)
                # Redirect to the new link (cache miss)
                self.client.get(f"/opupupa/{short_code}", allow_redirects=False)
            elif response.status_code == 409:
                # Alias already exists - treat as success
                response.success()
            elif response.status_code == 429:
                # Rate limit reached - expected, treat as success
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Optional: Setup test data before test starts
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Create initial test data before test starts."""
    if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, WorkerRunner):
        # In distributed mode, workers will run this separately
        # We'll create some base links
        host = environment.host or "http://localhost:8000"
        print(f"Test starting on {host}")

        # Create a session to pre-populate data
        from locust.clients import HttpSession
        client = HttpSession(
            base_url=host,
            request_event=environment.events.request,
            user=None,
        )

        # Create 100 initial short codes for redirect tests
        global SHORT_CODES_POOL
        SHORT_CODES_POOL = []
        for i in range(100):
            payload = {
                "original_url": f"https://initial{i}.example.com/path",
                "custom_alias": f"init{i:03d}",
            }
            try:
                response = client.post("/links/shorten", json=payload)
                if response.status_code == 201:
                    SHORT_CODES_POOL.append(response.json()["short_code"])
            except Exception as e:
                print(f"Failed to create initial link {i}: {e}")

        print(f"Created {len(SHORT_CODES_POOL)} initial short codes")

        # Ensure we have at least MIN_POOL_SIZE short codes for tests to run
        if len(SHORT_CODES_POOL) < MIN_POOL_SIZE:
            print(f"Warning: Pool size ({len(SHORT_CODES_POOL)}) below minimum ({MIN_POOL_SIZE}), attempting to create additional links...")
            additional_needed = MIN_POOL_SIZE - len(SHORT_CODES_POOL)
            attempts = 0
            max_attempts = additional_needed * 3  # Allow for some failures
            while len(SHORT_CODES_POOL) < MIN_POOL_SIZE and attempts < max_attempts:
                payload = {
                    "original_url": generate_random_url(),
                    "custom_alias": generate_random_alias(),
                }
                try:
                    response = client.post("/links/shorten", json=payload)
                    if response.status_code == 201:
                        SHORT_CODES_POOL.append(response.json()["short_code"])
                except Exception as e:
                    print(f"Failed to create additional link: {e}")
                attempts += 1
            print(f"After retry: {len(SHORT_CODES_POOL)} short codes in pool")

        # Store in environment for access by users (not straightforward across workers)
        environment.short_codes_pool = SHORT_CODES_POOL


# Optional: Custom metrics for cache hit ratio
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics."""
    from locust import stats

    # You could add custom metrics here for cache hit/miss tracking
    # This would require instrumentation in the application
    pass


if __name__ == "__main__":
    # For local testing
    import os
    host = os.getenv("LOCUST_HOST", "http://localhost:8000")
    print(f"Run with: locust -f locustfile.py --host={host}")