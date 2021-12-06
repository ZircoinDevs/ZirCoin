from .logger import Logger
from time import time, sleep
import multiprocessing
logger = Logger("miner")


class Miner:
    def __init__(self, blockchain, protocol, wallet, config, consensus):
        self.blockchain = blockchain
        self.protocol = protocol
        self.wallet = wallet
        self.config = config
        self.consensus = consensus
    
    def mine_threaded(self):
        while True:
            try:
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

    def mine(self):
        logger.info("⛏  Mining now...")
        processes = []
        for i in range(0,int(multiprocessing.cpu_count()),1):
            process = multiprocessing.Process(target=Miner.mine_threaded(self))
            processes.append(process)
            process.start()
            print("For now, just do a ctrl+c as many times as there are threads in your CPU."")
            
