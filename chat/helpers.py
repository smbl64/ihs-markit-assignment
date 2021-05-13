import urllib.request


def fibonacci(n: int) -> int:
    """
    A naive fibonacci implementation to simulate CPU load.
    """
    if n < 1:
        raise ValueError("n must be greater than zero")

    if n == 1 or n == 2:
        return 1

    return fibonacci(n - 1) + fibonacci(n - 2)


def get_remote_resource_length(url: str) -> int:
    with urllib.request.urlopen(url) as response:
        data = response.read()
        return len(data)
