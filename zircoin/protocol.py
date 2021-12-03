import json

from aiohttp import web
import requests

from .version import PROTOCOL_VERSION
from .logger import Logger

logger = Logger("networking")


class Protocol:
    def __init__(self, blockchain, connection_pool, server_config, config, node_id):
        self.server_config = server_config
        self.main_config = config
        self.blockchain = blockchain
        self.connection_pool = connection_pool

        self.connection_errors = (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.HTTPError
        )

        self.version = PROTOCOL_VERSION

        self.node_id = node_id

    # Methods

    def broadcast_block(self, block):
        if self.blockchain.last_block:
            peers = self.connection_pool.get_peers_with_blockhash(
                self.blockchain.chain[-1]["hash"], 20)
        else:
            peers = self.connection_pool.get_alive_peers(20)

        for peer in peers:
            try:
                requests.post(peer + "/block-recv", json.dumps(block))
            except self.connection_errors:
                continue

    def broadcast_transaction(self, transaction):
        peers = self.connection_pool.get_alive_peers(20)

        for peer in peers:
            try:
                requests.post(peer + "/tx-recv", json.dumps(transaction))
            except self.connection_errors:
                continue

    # AIOHTTP Routes

    def home_route(self, request):
        return web.Response(text="ZirCoin Node")

    # returns blockchain
    def blockchain_route(self, request):
        return web.json_response(self.blockchain.chain)

    def latest_block_route(self, request):
        return web.json_response(self.blockchain.last_block)

    # returns a list of block hashes
    def blockinv_route(self, request):
        return web.json_response(self.blockchain.block_inv)

    # returns peer info
    def info_route(self, request):
        return web.json_response({
            "protocol": self.version,
            "block_height": self.blockchain.height,
            "node_id": self.node_id,
            "blockchain_id": self.main_config["blockchain_id"]
        })

    # adds the pinging peer to the connection pool
    async def ping_route(self, request):
        response = await request.json()
        port = response["port"]
        ip = request.transport.get_extra_info('peername')[0]
        addr = (ip, port)
        print("Pinged by: " + str(addr))
        self.connection_pool.add_tuple_addr(addr)
        return web.Response(text="pong")

    # returns list of connected peers
    def peers_route(self, request):
        return web.json_response(list(self.connection_pool.pool))

    # returns list of pending transactions
    def transactions_route(self, request):
        return web.json_response(self.blockchain.transaction_pool.pool)

    # returns a list of transactions that have been mined, but have not been validated yet.
    def unconfirmed_transactions_route(self, request):
        return web.json_response(self.blockchain.transaction_pool.unconfirmed_pool)

    # endpoint for newly mined blocks to be sent to
    async def block_receive_route(self, request):
        try:
            block = await request.json()
        except json.decoder.JSONDecodeError:
            return web.Response(text="Invalid JSON")

        if not self.blockchain.add(block):
            return web.Response(text="Invalid block")

        return web.Response(text="Received")

    # endpoint for new transactions to be sent to
    async def transaction_recieve_route(self, request):
        try:
            transaction = await request.json()
        except json.decoder.JSONDecodeError:
            return web.Response(text="Invalid JSON")

        if not self.blockchain.transaction_pool.add(transaction):
            return web.Response(text="Invalid transaction")

        return web.Response(text="received")

    # returns the block associated with said hash
    def block_route(self, request):
        block_hash = request.match_info.get("blockhash")
        block = self.blockchain.get_block_from_hash(block_hash)
        if block:
            return web.json_response(block)
