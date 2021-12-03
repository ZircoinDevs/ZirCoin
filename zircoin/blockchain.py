import math
import json
import pickle
from hashlib import sha256
from time import time
from random import getrandbits

from .logger import Logger
from .transactions import TransactionPool

miner = Logger("miner")
bc = Logger("blockchain")


class Blockchain():
    def __init__(self, blockchain_id, create_genesis_block=True):
        self.chain = []
        self.transaction_pool = TransactionPool(self)
        self.target = "00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.blockchain_id = blockchain_id
        if create_genesis_block:
            self.chain.append(self.make_genesis_block())

    def __str__(self):
        text = ""
        for block in self.chain:
            text += self.display_block(block) + '\n'

        return text

    @staticmethod
    def display_block(block):
        text = ""

        for key, value in block.items():
            text += f"{key}: {value}\n"

        return text

    @property
    def block_reward(self):
        reward = 5
        for i in range(1, self.height):
            if i % 4000 == 0:
                reward *= 0.5

        return reward

    def save(self):
        with open("blockchain.json", "w") as f:
            json.dump(self.chain, f)

    def load(self):
        with open("blockchain.json", "r") as f:
            try:
                blockchain = json.load(f)
            except json.decoder.JSONDecodeError:
                return False

            if len(blockchain) > len(self.chain):
                self.chain = blockchain
                bc.info("Loaded blockchain from blockchain.json")
                self.target = self.last_block["target"]
                self.calculate_target()
            else:
                return False

        return True

    def make_genesis_block(self):
        block = {
            "height": len(self.chain),
            "time": time(),
            "blockchain_id": self.blockchain_id,
            "transactions": [],
            "previous_hash": None,
            "target": self.target,
            "nonce": format(getrandbits(64), 'x')
        }

        block = self.hash(block)

        return block

    def make_block(self, wallet):
        block = {
            "height": self.height + 1,
            "time": time(),
            "blockchain_id": self.blockchain_id,
            "transactions": self.transaction_pool.get_pending_transactions(self.transaction_inv),
            "previous_hash": self.previous_hash,
            "target": self.target,
            "nonce": format(getrandbits(64), 'x')
        }

        coinbase_transaction = self.transaction_pool.create_coinbase_transaction(
            wallet.public_key, self.block_reward)
        block["transactions"].insert(0, coinbase_transaction)

        block = self.hash(block)

        return block

    @staticmethod
    def hash(block):
        block_str = json.dumps(block, sort_keys=True).encode()
        block["hash"] = sha256(block_str).hexdigest()

        return block

    def contains_hash(self, block_hash):
        for block in self.chain:
            if block["hash"] == block_hash:
                return True

        return False

    @property
    def previous_hash(self):
        if self.last_block:
            return self.last_block["hash"]
        else:
            return None

    @property
    def last_block(self):
        if self.chain:
            return self.chain[-1]
        else:
            return None

    @property
    def height(self):
        last_block = self.last_block
        if last_block:
            return last_block["height"]
        else:
            return None

    @property
    def block_inv(self):
        inventory = []
        for block in self.chain:
            inventory.append(block["hash"])

        return inventory

    @property
    def transaction_inv(self):
        inventory = []
        for block in self.chain:
            for transaction in block["transactions"]:
                inventory.append(transaction)

        return inventory

    def add(self, block, verbose=False):
        if self.validate(block, verbose=verbose):
            self.chain.append(block)
            self.transaction_pool.update_pool(self.chain)
            self.save()
            return True
        else:
            return False

    def valid_pow(self, block):
        return block["hash"] < self.target

    def validate(self, block, verbose=False):
        self.calculate_target()

        # check that the block is from the correct blockchain
        if block["blockchain_id"] != self.blockchain_id:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Block is from a different blockchain")
            return False

        # if the block is already in the blockchain, the block is invalid
        if block["hash"] in self.block_inv:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Block already in blockchain")
            return False

        # if the previous hash is not correct, the block is invalid
        if block["previous_hash"] != self.previous_hash:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Previous hash is incorrect")
            return False

        # if it is a genesis block, dont check it
        if block["height"] == 0:
            if self.height is None:
                return True
            else:
                if verbose:
                    bc.error(
                        "Block #" + str(block["height"]) + " is invalid: Genesis block is already added")
                return False

        # validate height
        if block["height"] != self.height + 1:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Height is incorrect")
                print(block["height"], self.height)
            return False

        if self.last_block:
            if block["height"] != self.last_block["height"] + 1:
                if verbose:
                    bc.error(
                        "Block #" + str(block["height"]) + " is invalid: Height is not correct")
                return False
        elif block["height"] != 0:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Genesis block has to be added first")
            return False

        # validate trasactions
        if not self.validate_block_transactions(block):
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Invalid transactions detected")
            return False

        # validate timestamp
        if self.last_block:
            if block["time"] < self.last_block["time"]:  # in the past
                if verbose:
                    bc.error(
                        "Block #" + str(block["height"]) + " is invalid: Timestamp is in the past")
                return False
            if block["time"] > time():  # in the future
                if verbose:
                    bc.error(
                        "Block #" + str(block["height"]) + " is invalid: Timestamp is in the future")
                return False

        # validate proof of work
        new_block = block.copy()
        del new_block["hash"]
        new_block = json.dumps(new_block, sort_keys=True).encode()

        if not sha256(new_block).hexdigest() == block["hash"]:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Hash is invalid")
            return False

        if self.valid_pow(block):
            return True
        else:
            if verbose:
                bc.error(
                    "Block #" + str(block["height"]) + " is invalid: Proof of work is invalid")
            return False

    @staticmethod
    def get_balance_from_block(block, public_key, stop_at_txid=""):
        balance = 0.0
        for transaction in block["transactions"]:
            if transaction["receiver"] == public_key:
                balance += transaction["amount"]
            if transaction["sender"] == public_key:
                balance -= transaction["amount"]

            if transaction["id"] == stop_at_txid:
                return balance

        return balance

    def check_for_overspent_transactions(self, block):
        for transaction in block["transactions"]:
            if transaction["type"] == "coinbase":
                continue

            balance = self.get_balance(transaction["sender"]) + \
                self.get_balance_from_block(
                    block, transaction["sender"], stop_at_txid=transaction["id"])

            if balance < 0:
                return False

        return True

    def validate_block_transactions(self, block):
        # if there are no transactions, the tx is invalid
        if len(block["transactions"]) < 1:
            return False

        # if the first transaction is not a coinbase transaction, the block is invalid
        if block["transactions"][0]["type"] != "coinbase":
            return False

        # if there are multiple coinbase transactions, the block is invalid
        for transaction in block["transactions"][1:len(block["transactions"])]:
            if transaction["type"] == "coinbase":
                return False

        # if the block reward is too high, the block is invalid
        if block["transactions"][0]["amount"] != self.block_reward:
            return False

        if not self.check_for_overspent_transactions(block):
            return False

        for i in range(1, len(block["transactions"])):
            transaction = block["transactions"][i]

            if not self.transaction_pool.validate_transaction(transaction):
                return False

        return True

    def calculate_target(self, print_block_times=False):
        if not self.height:
            return False

        # dont do anything if the difficulty has already been calculated
        if self.target != self.last_block["target"]:
            return False

        interval = 40

        if (self.height + 1) % interval == 0:

            # Expected time span of 10 blocks
            expected_timespan = 60 * interval

            # Calculate the actual time span
            actual_timespan = self.chain[-1]["time"] - \
                self.chain[-interval]["time"]

            entire_span = self.chain[-1]["time"] - self.chain[1]["time"]
            block_time = entire_span / self.height

            if print_block_times:
                miner.info("Average block time: " +
                           str(round(block_time, 4)) + "s")

            # figure out what the offset is
            ratio = actual_timespan / expected_timespan

            # Calculate the new target by multiplying the current one by the ratio
            new_target = int(self.target, 16) * ratio
            self.target = format(math.floor(new_target), "x").zfill(64)

            return True

        return False

    def get_blocks_after_timestamp(self, timestamp):
        blocks = []
        for block in self.chain:
            if block["timestamp"] < timestamp:
                blocks.append(block)
            else:
                return blocks

    def get_balance(self, public_key):
        balance = 0.0

        for block in self.chain:
            for transaction in block["transactions"]:
                if transaction["receiver"] == public_key:
                    balance += transaction["amount"]
                if transaction["sender"] == public_key:
                    balance -= transaction["amount"]

        return balance

    def get_block_from_hash(self, block_hash):
        for block in self.chain:
            if block["hash"] == block_hash:
                return block

        return None

    def mine_new_block(self, wallet):

        if self.calculate_target(print_block_times=True):
            miner.info("New mining target: " + str(self.target))

        # generate new blocks until a valid one is found
        start = time()

        block_to_mine = self.height + 1

        block = self.make_block(wallet)
        while not self.valid_pow(block):
            if self.height >= block_to_mine:
                miner.info(f"✗ Failed to mine block #{block_to_mine}")
                return None

            block = self.make_block(wallet)

        end = time()
        time_taken = end - start

        # if the block is invalid, don't add it
        if not self.validate(block, verbose=True):
            miner.error("Invalid block")
            return None

        height = block["height"]
        miner.info(f"✓ Mined block #{height} in {round(time_taken, 2)}s")

        return block

    def clear(self, create_genesis_block=False):
        self.__init__(self.blockchain_id,
                      create_genesis_block=create_genesis_block)
