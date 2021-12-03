import nacl
import json
from .logger import Logger
import os

logger = Logger("Wallet")


class Wallet:
    def __init__(self, wallet_file="wallet.json"):
        if not self.load_wallet(wallet_file):

            if os.stat(wallet_file).st_size != 0:
                # logger.error(
                #    f"The file '{wallet_file}' is not empty, so a new wallet could not be created.", fatal=True)
                logger.error(
                    f"Could not load wallet from '{wallet_file}'.", fatal=True)

            self.create_new_wallet(wallet_file)

            logger.info("New wallet created.")
            logger.urgent("You MUST back up your wallet in case it is lost. Copy " +
                          wallet_file + " to a safe location.")
        else:
            logger.info("Loaded wallet")

    def load_wallet(self, wallet_file):
        try:
            with open(wallet_file, "r") as f:
                keys = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return False

        self.private_key = keys["private_key"]
        self.public_key = keys["public_key"]

        return True

    def create_new_wallet(self, wallet_file):
        keys = self.generate_keys()
        try:
            with open(wallet_file, "a") as f:
                json.dump(keys, f, indent=4, sort_keys=True)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return False

        self.private_key = keys["private_key"]
        self.public_key = keys["public_key"]

    def generate_keys(self):

        # create public and private RSA keys
        private_key = nacl.signing.SigningKey.generate()
        public_key = private_key.verify_key

        keys = {
            "private_key": private_key.encode(encoder=nacl.encoding.HexEncoder).decode(),
            "public_key": public_key.encode(encoder=nacl.encoding.HexEncoder).decode(),
        }

        return keys
