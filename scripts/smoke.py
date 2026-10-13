import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = (
    sys.argv[1] if len(sys.argv) > 1
    else "http://127.0.0.1:5000"
).rstrip("/")


def request_json(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    request = Request(BASE_URL + path, data=data, headers=headers)

    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    for attempt in range(10):
        try:
            status, body = request_json("/")
            check(status == 200, f"Home returned HTTP {status}")
            check(
                isinstance(body, dict)
                and body.get("service") == "iris-prediction",
                "Unexpected home service identity",
            )
            break
        except (URLError, TimeoutError, ValueError, RuntimeError) as error:
            if attempt == 9:
                raise RuntimeError("Service did not become ready") from error
            time.sleep(1)

    status, body = request_json(
        "/predict", {"measurements": [5.1, 3.5, 1.4, 0.2]}
    )
    check(status == 200, f"Valid prediction returned HTTP {status}")
    check(
        isinstance(body, dict) and body.get("prediction") == "setosa",
        "Unexpected prediction",
    )

    status, body = request_json(
        "/predict", {"measurements": [5.1, 3.5]}
    )
    check(status == 400, f"Invalid input returned HTTP {status}")
    check(
        isinstance(body, dict)
        and isinstance(body.get("error"), str)
        and bool(body["error"].strip()),
        "Invalid input did not return an error message",
    )

    print("Smoke checks passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Smoke checks failed: {error}", file=sys.stderr)
        sys.exit(1)