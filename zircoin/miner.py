from .logger import Logger
from time import time
logger = Logger("miner")


class Miner:
    def __init__(self, blockchain, protocol, wallet, config, consensus):
        self.blockchain = blockchain
        self.protocol = protocol
        self.wallet = wallet
        self.config = config
        self.consensus = consensus

    def mine(self):
        logger.info("⛏  Mining now...")
        while True:
            try:
                if self.consensus.sync_status["syncing"]:
                    logger.info("Waiting for blockchain sync to complete...")
                    while self.consensus.sync_status["syncing"]:
                        continue
                    logger.info("Sync completed.")

                block = self.blockchain.mine_new_block(self.wallet)
                if not block:
                    continue

                if self.config["fullnode"]:
                    self.blockchain.add(block)
                else:
                    self.protocol.broadcast_block(block)

                # if the block is not accepted in 5 seconds, start mining a new block
                timeout = time() + 5
                while not self.blockchain.contains_hash(block["hash"]):
                    if time() >= timeout or self.blockchain.height > block["height"]:
                        height = block["height"]
                        logger.info(f"✗ Block #{height} not accepted")
                        break

            except KeyboardInterrupt:
                break
