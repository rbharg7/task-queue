import time
import math
import random

def add(a: int, b: int) -> int:
    time.sleep(2)
    return a + b

def multiply(a: int, b: int) -> int:
    time.sleep(3)
    return a * b

def factorial(n: int) -> int:
    time.sleep(2)
    return math.factorial(n)

def flaky(message: str) -> str:
    """Fails 70% of the time — simulates unreliable external API"""
    time.sleep(1)
    if random.random() < 0.7:
        raise ConnectionError("Simulated network failure")
    return f"Success: {message}"

TASK_REGISTRY = {
    "add": add,
    "multiply": multiply,
    "factorial": factorial,
    "flaky": flaky,
}