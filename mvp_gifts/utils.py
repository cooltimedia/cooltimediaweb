"""
Utility functions for the Gift Profile MVP.
"""

from datetime import datetime
import secrets
import string


def generate_event_token():
    """
    Generate a unique URL-safe token for a gift event.

    The token is composed of:
    - A timestamp with year, month, day, hour, minute, second, and microseconds.
    - A secure random suffix using lowercase letters and digits.

    Returns:
        str: A unique token string suitable for public sharing URLs.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    characters = string.ascii_lowercase + string.digits
    suffix = "".join(secrets.choice(characters) for _ in range(4))

    return f"{timestamp}{suffix}"