from zircoin.wallet import Wallet
from zircoin.miner import Miner
from zircoin.logger import Logger
from zircoin.server import Server
from zircoin.consensus import Consensus
from zircoin.networking import HttpRoutes
from zircoin.connections import ConnectionPool
from zircoin.blockchain import Blockchain
from zircoin.version import PROTOCOL_VERSION, NETWORKING_VERSION, SOFTWARE_VERSION
from zircoin.utils import test_hashrate

import json
from hashlib import sha256
from random import getrandbits
from time import sleep

from threading import Thread



class Client():

    def __init__(self, CONFIG=json.load(open("config.json", "r")), blockchain_file="blockchain.json"):

        self.NODE_ID = sha256(str(getrandbits(256)).encode()).hexdigest()
        self.CONFIG = CONFIG
        self.SERVER_CONFIG = {
            "ip": "0.0.0.0",
            "port": 2227
        }

        self.blockchain = Blockchain(self.CONFIG["blockchain_id"], file=blockchain_file)
        self.blockchain.load()

        self.connection_pool = ConnectionPool(
            CONFIG,
            self.NODE_ID,
            2227
        )

        self.http_routes = HttpRoutes(
            self.blockchain,
            self.connection_pool,
            self.SERVER_CONFIG,
            self.CONFIG,
            self.NODE_ID
        )

        self.consensus = Consensus(
            self.blockchain,
            self.connection_pool
        )

        self.miner = Miner(
            self.blockchain,
            self.CONFIG,
            self.consensus,
            self.connection_pool
        )

        self.start_threads()

    def start_threads(self):
        self.connection_pool.add_seed_nodes()

        self.consensus_thread = Thread(target=self.consensus.consensus, name="consensus")
        self.consensus_thread.daemon = True
        self.consensus_thread.start()
        sleep(0.1)

        self.transaction_consensus_thread = Thread(
            target=self.consensus.transaction_consensus, name="txconsensus")
        self.transaction_consensus_thread.daemon = True
        self.transaction_consensus_thread.start()
        sleep(0.1)