import urllib.request
import hashlib
import time
from .logger import Logger

logger = Logger("utils")


def get_public_ip():
    try:
        ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
        return ip
    except Exception:
        logger.error("Could not get public ip from ident.me", fatal=True)


def test_hashrate():
    timeout = time.time() + 5

    nonce = 0
    hashes = 0

    while True:
        if time.time() >= timeout:
            break

        nonce += 1
        hashlib.sha256(str(nonce).encode()).hexdigest()
        hashes += 1

    return hashes/5
