from aiohttp import web
import asyncio
from json import loads

from .connections import ConnectionPool
from .miner import Miner
from .utils import get_public_ip
from .logger import Logger
logger = Logger("server")


class Server:
    def __init__(self, blockchain, http_routes, server_config):
        self.blockchain = blockchain
        self.http_routes = http_routes
        self.server_config = server_config
    
    def aiohttp_server(self):
        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.http_routes.home_route),
            web.get('/blockchain', self.http_routes.blockchain_route),
            web.get('/latest-block', self.http_routes.latest_block_route),
            web.get('/blockinv', self.http_routes.blockinv_route),
            web.get('/info', self.http_routes.info_route),
            web.post('/ping', self.http_routes.ping_route),
            web.get('/peers', self.http_routes.peers_route),
            web.get('/pending-transactions', self.http_routes.transactions_route),
            web.get('/unconfirmed-transactions', self.http_routes.unconfirmed_transactions_route),

            web.post('/block-recv', self.http_routes.block_receive_route),
            web.post('/tx-recv', self.http_routes.transaction_recieve_route),

            web.get('/block/{blockhash}', self.http_routes.block_route)
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
