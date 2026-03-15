import random
import string
from datetime import datetime, timezone, timedelta
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

SHORT_CODES_POOL = []
MIN_POOL_SIZE = 10

def generate_random_url():
    domain = ''.join(random.choices(string.ascii_lowercase, k=10))
    path = ''.join(random.choices(string.ascii_lowercase, k=5))
    return f"https://{domain}.example.com/{path}"


def generate_random_alias():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


class LinkCreationUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def create_link_with_random_alias(self):
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 409:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def create_link_without_alias(self):
        payload = {
            "original_url": generate_random_url(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 409:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class RedirectUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(10)
    def redirect_to_short_link(self):
        if not SHORT_CODES_POOL:
            return

        short_code = random.choice(SHORT_CODES_POOL)
        self.client.get(f"/opupupa/{short_code}", allow_redirects=False)

    @task(1)
    def create_link(self):
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                short_code = response.json()["short_code"]
                SHORT_CODES_POOL.append(short_code)
            elif response.status_code == 409:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class CacheEfficiencyUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(8)
    def redirect_cached(self):
        if not SHORT_CODES_POOL:
            return

        short_code = random.choice(SHORT_CODES_POOL)
        self.client.get(f"/opupupa/{short_code}", allow_redirects=False)

    @task(2)
    def redirect_uncached(self):
        payload = {
            "original_url": generate_random_url(),
            "custom_alias": generate_random_alias(),
        }
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
                short_code = response.json()["short_code"]
                SHORT_CODES_POOL.append(short_code)

                self.client.get(f"/opupupa/{short_code}", allow_redirects=False)
            elif response.status_code == 409:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, WorkerRunner):
        host = environment.host or "http://localhost:8000"
        print(f"Test starting on {host}")

        from locust.clients import HttpSession
        client = HttpSession(
            base_url=host,
            request_event=environment.events.request,
            user=None,
        )

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

        if len(SHORT_CODES_POOL) < MIN_POOL_SIZE:
            print(f"Warning: Pool size ({len(SHORT_CODES_POOL)}) below minimum ({MIN_POOL_SIZE}), attempting to create additional links...")
            additional_needed = MIN_POOL_SIZE - len(SHORT_CODES_POOL)
            attempts = 0
            max_attempts = additional_needed * 3  
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

        environment.short_codes_pool = SHORT_CODES_POOL



if __name__ == "__main__":
    import os
    host = os.getenv("LOCUST_HOST", "http://localhost:8000")
    print(f"Run with: locust -f locustfile.py --host={host}")