from .logger import Logger
from time import time, sleep
import multiprocessing
logger = Logger("miner")


class Miner:
    def __init__(self, blockchain, http_routes, wallet, config, consensus):
        self.blockchain = blockchain
        self.http_routes = http_routes
        self.wallet = wallet
        self.config = config
        self.consensus = consensus

    def mine_threaded(self):
        try:
            while True:
                if self.consensus.sync_status["syncing"]:
                    logger.info("Waiting for blockchain sync to complete...")
                    while self.consensus.sync_status["syncing"]:
                        sleep(0.5)
                    logger.info("Sync completed.")
                block = self.blockchain.mine_new_block(self.wallet)
                if not block:
                    continue

                if self.config["fullnode"]:
                    self.blockchain.add(block)
                else:
                    self.http_routes.broadcast_block(block)

                mined_block = True
                height = block["height"]
                _hash = block["hash"]

                # if the block is not accepted in 5 seconds, start mining a new block
                timeout = time() + 5
                while not self.blockchain.contains_hash(block["hash"]):
                    if time() >= timeout or self.blockchain.height > block["height"]:
                        logger.info(f"✗ Block #{height} not accepted")
                        mined_block = False
                        break

            if mined_block:
                logger.info(f"✓ Mined block #{height} ({_hash})")
        except KeyboardInterrupt:
            return

    def mine(self):
        logger.info("⛏  Mining now...")
        try:
            processes = []
            for i in range(0,int(multiprocessing.cpu_count()),1):
                process = multiprocessing.Process(target=self.mine_threaded)
                processes.append(process)
                process.start()
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            return