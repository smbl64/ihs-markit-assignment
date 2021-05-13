def fibonacci(n: int) -> int:
    """
    A naive fibonacci implementation to simulate CPU load.
    """
    if n < 1:
        raise ValueError("n must be greater than zero")

    if n == 1 or n == 2:
        return 1

    return fibonacci(n - 1) + fibonacci(n - 2)
