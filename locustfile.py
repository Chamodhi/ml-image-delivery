from locust import HttpUser, between, events, task


class IrisUser(HttpUser):
    wait_time = between(1, 2)

    def check_response(self, response, expected):
        if response.status_code != 200:
            response.failure(f"Expected HTTP 200, got {response.status_code}")
            return

        try:
            body = response.json()
        except ValueError:
            response.failure("Response was not valid JSON")
            return

        if not isinstance(body, dict):
            response.failure("Expected a JSON object")
            return

        for key, value in expected.items():
            if body.get(key) != value:
                response.failure(f"Unexpected value for {key}")
                return

    @task(3)
    def predict(self):
        with self.client.post(
            "/predict",
            json={"measurements": [5.1, 3.5, 1.4, 0.2]},
            timeout=5,
            catch_response=True,
        ) as response:
            self.check_response(response, {"prediction": "setosa"})

    @task(1)
    def home(self):
        with self.client.get(
            "/",
            timeout=5,
            catch_response=True,
        ) as response:
            self.check_response(response, {"service": "iris-prediction"})


@events.quitting.add_listener
def performance_gate(environment, **kwargs):
    total = environment.stats.total
    p95 = total.get_response_time_percentile(0.95)

    passed = (
        total.num_requests >= 20
        and total.fail_ratio <= 0.01
        and p95 is not None
        and p95 <= 1000
    )

    environment.process_exit_code = 0 if passed else 1

    print(
        f"Gate {'PASS' if passed else 'FAIL'}: "
        f"requests={total.num_requests}, "
        f"failure_ratio={total.fail_ratio:.4f}, "
        f"p95_ms={p95}"
    )