import requests
import json
from more_itertools import take
from time import sleep, time
from threading import Thread

from .logger import Logger
from .version import PROTOCOL_VERSION, NETWORKING_VERSION

logger = Logger("connections")


class ConnectionPool:
    def __init__(self, config, node_id, server_port):
        self.pool = set()
        self.inactive_pool = set()

        self.max_connections = 20
        self.config = config
        self.node_id = node_id
        self.server_port = server_port

        self.NETWORKING_VERSION = NETWORKING_VERSION
        self.PROTOCOL_VERSION = PROTOCOL_VERSION

        self.connection_errors = (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.HTTPError
        )

        self.node_discovery_thread = Thread(target=self.discover_nodes, daemon=True)
        self.node_discovery_thread.start()

        logger.info("Initialised connection pool")

    @property
    def node_ids(self):
        node_ids = []
        for peer in self.pool.copy():
            try:
                info = requests.get(peer + "/info", timeout=0.5).json()
            except self.connection_errors:
                continue

            node_ids.append(info["node_id"])

        return node_ids

    def add_seed_nodes(self):
        if "seed_nodes" in self.config:
            for node in self.config["seed_nodes"]:
                self.add(self.get_url(node))

        self.update_pool()

    def add_tuple_addr(self, addr):
        text_addr = addr[0] + ":" + str(addr[1])
        self.add(self.get_url(text_addr))

    def get_url(self, addr):
        if "http" not in addr:
            addr = f"http://{addr}"

        if ":" not in addr and self.config["multiport_mode"]:
            addr = f"{addr}:2227"

        if ':' in addr and not self.config["multiport_mode"]:
            addr = addr.split(":", 1)[0]

        return addr

    def broadcast(self, payload, route, send_to_all=False):
        if not send_to_all:
            for node in self.get_alive_peers(20):
                try:
                    requests.post(node + route, payload)
                except self.connection_errors:
                    continue
        else:
            for node in self.pool:
                try:
                    requests.post(self.get_url(node) + route, payload)
                except self.connection_errors:
                    continue

    def get_peers_with_blockhash(self, _hash, amount):
        peers = []
        for peer in self.pool.copy():
            if len(peers) == amount:
                break

            try:
                latest_block = requests.get(peer + "/latest-block").json()
            except self.connection_errors:
                continue

            if latest_block["hash"] == _hash:
                peers.append(peer)

        return peers

    def add(self, addr):
        if len(self.pool) >= self.max_connections:
            return False

        if addr in self.pool:
            return False

        try:
            info = requests.get(addr + "/info", timeout=2).json()

        except self.connection_errors:
            return False  # if the node is unreachable, don't add it

        # prevents connection to self
        if info["node_id"] == self.node_id:
            return False
        # prevents nodes being added multiple times
        if info["node_id"] in self.node_ids:
            return False

        if (info["networking_version"].split('.', 2)[0] != self.NETWORKING_VERSION.split('.', 2)[0] or
            info["networking_version"].split('.', 2)[1] != self.NETWORKING_VERSION.split('.', 2)[1]):
            return False

        if (info["protocol_version"].split('.', 2)[0] != self.PROTOCOL_VERSION.split('.', 2)[0] or
            info["protocol_version"].split('.', 2)[1] != self.PROTOCOL_VERSION.split('.', 2)[1]):
            return False

        if info["blockchain_id"] != self.config["blockchain_id"]:
            return False

        self.pool.add(addr)

        if self.config["fullnode"]:
                requests.post(addr + "/ping", json.dumps({"port": self.server_port}))

    def remove(self, addr):
        try:
            self.pool.remove(addr)
        except ValueError:
            return False

    def update_pool(self):
        # moves any active nodes in the inactive connections pool to the main pool

        for peer in self.inactive_pool.copy():
            if peer in self.pool:
                self.pool.remove(peer)

            try:
                if requests.get(peer, timeout=2) and self.add(peer):
                    self.inactive_pool.remove(peer)
            except self.connection_errors:
                continue

        for peer in self.pool.copy():
            if peer in self.inactive_pool:
                self.inactive_pool.remove(peer)

            try:
                if requests.get(peer, timeout=1):
                    continue
            except self.connection_errors:
                if peer in self.pool:
                    self.pool.remove(peer)

                self.inactive_pool.add(peer)

    def discover_nodes(self):
        while True:
            if len(self.pool) >= self.max_connections:
                return False

            start = time()

            for peer in self.pool.copy():
                if len(self.pool) >= self.max_connections:
                    break

                try:
                    peers = requests.get(peer + "/peers", timeout=2).json()
                except self.connection_errors:
                    try:
                        self.pool.remove(peer)
                    except KeyError:
                        pass

                for peer in peers:
                    self.add(peer)

            total_time = time() - start
            sleep(max(0, (30 - total_time)))

    def get_alive_peers(self, amount):
        self.update_pool()
        return take(amount, self.pool.copy())
