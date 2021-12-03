import urllib.request
from .logger import Logger

logger = Logger("utils")

def get_public_ip():
    try:
        ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
        return ip
    except Exception:
        logger.error("Could not get public ip from ident.me", fatal=True)
