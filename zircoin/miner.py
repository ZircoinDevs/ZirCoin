from .logger import Logger
from .messages import broadcast_block
from time import time, sleep
logger = Logger("miner")


class Miner:
    def __init__(self, blockchain, config, consensus, connection_pool, verbose=True):
        self.blockchain = blockchain
        self.config = config
        self.consensus = consensus
        self.connection_pool = connection_pool

        self.verbose = verbose

    def mine(self, wallet):
        if self.verbose: logger.info("⛏  Mining now...")
        while True:
            try:
                if self.consensus.sync_status["syncing"]:
                    if self.verbose: logger.info("Waiting for blockchain sync to complete...")
                    while self.consensus.sync_status["syncing"]:
                        sleep(0.5)
                    if self.verbose: logger.info("Sync completed.")

                block = self.blockchain.mine_new_block(wallet)
                if not block:
                    continue

                if self.config["fullnode"]:
                    self.blockchain.add(block)
                else:
                    broadcast_block(block, self.connection_pool, self.blockchain)

                mined_block = True
                height = block["height"]
                _hash = block["hash"]

                # if the block is not accepted in 5 seconds, start mining a new block
                timeout = time() + 5
                while not self.blockchain.contains_hash(block["hash"]):
                    if time() >= timeout or self.blockchain.height > block["height"]:
                        if self.verbose: logger.info(f"✗ Block #{height} not accepted")
                        mined_block = False
                        break

                if mined_block:
                    if self.verbose: logger.info(
                        f"✓ Mined block #{height} ({_hash})")

            except KeyboardInterrupt:
                break
