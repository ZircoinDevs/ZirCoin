from aiohttp import web
import asyncio
from json import loads

from .connections import ConnectionPool
from .protocol import Protocol
from .miner import Miner
from .utils import get_public_ip
from .logger import Logger
logger = Logger("server")


class Server:
    def __init__(self, blockchain, protocol, server_config):
        self.blockchain = blockchain
        self.protocol = protocol
        self.server_config = server_config
    
    def aiohttp_server(self):
        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.protocol.home_route),
            web.get('/blockchain', self.protocol.blockchain_route),
            web.get('/latest-block', self.protocol.latest_block_route),
            web.get('/blockinv', self.protocol.blockinv_route),
            web.get('/info', self.protocol.info_route),
            web.post('/ping', self.protocol.ping_route),
            web.get('/peers', self.protocol.peers_route),
            web.get('/pending-transactions', self.protocol.transactions_route),
            web.get('/unconfirmed-transactions', self.protocol.unconfirmed_transactions_route),

            web.post('/block-recv', self.protocol.block_receive_route),
            web.post('/tx-recv', self.protocol.transaction_recieve_route),

            web.get('/block/{blockhash}', self.protocol.block_route)
        ])

        runner = web.AppRunner(self.app)
        return runner

    def start_server(self, runner):
        logger.info("Starting server...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        server = web.TCPSite(runner, host="0.0.0.0", port=self.server_config['port'])
        loop.run_until_complete(server.start())
        loop.run_forever()
