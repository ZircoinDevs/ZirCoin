from .logger import Logger
import sys

logger = Logger("Graphs")

try:
    import matplotlib.pyplot as plt
except ImportError:
    pass


def wealth_distribution(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    wallets = {}
    keys = []

    for block in blockchain.chain:
        for transaction in block["transactions"]:
            wallets[transaction["receiver"]] = 0

    for wallet in wallets:
        bal = blockchain.get_balance(wallet)
        if bal > 0:
            wallets[wallet] = bal

        keys.append(f"{wallet[0:3]}...{wallet[-3:]}")

    fig1, ax1 = plt.subplots()
    ax1.pie(wallets.values(), labels=keys, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    plt.title("Wealth distribution", fontdict={
              'family': 'sans-serif', 'color': 'black', 'size': 20}, pad=15)
    plt.show()

def transaction_volume(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    wallets = {}
    keys = []

    for block in blockchain.chain:
        for transaction in block["transactions"]:
            wallets[transaction["receiver"]] = 0

    for wallet in wallets:
        bal = 0.0

        for block in blockchain.chain:
            for transaction in block["transactions"]:
                if transaction["type"] == "coinbase":
                    continue

                if transaction["receiver"] == wallet or transaction["sender"] == wallet:
                    bal += transaction["amount"]
        
        if bal > 0:
            wallets[wallet] = bal

        keys.append(f"{wallet[0:3]}...{wallet[-3:]}")

    fig1, ax1 = plt.subplots()
    
    if len(set(wallets.values())) < 2:
        logger.info("Not enough data to show")
        return False

    ax1.pie(wallets.values(), labels=keys, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    plt.title("Transaction Volume", fontdict={
              'family': 'sans-serif', 'color': 'black', 'size': 20}, pad=15)
    plt.show()

def transaction_quantity(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False
    
    time = []
    transactions = []

    for block in blockchain.chain:
        time.append(block["time"])
        transactions.append(len(block["transactions"]))

    plt.plot(time, transactions)
    plt.title("Transaction quantity")
    plt.xlabel("Time (epoch unix timestamp)")
    plt.ylabel("Transactions per block")

    plt.show()

def coin_supply(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    time = []
    coins = []
    height = []

    supply = 0

    for block in blockchain.chain:
        time.append(round(block["time"]))

        if len(block["transactions"]) > 0:
            supply += block["transactions"][0]["amount"]
        
        coins.append(supply)
        height.append(block["height"])

    plt.plot(time, coins)
    plt.title("ZirCoin supply")
    plt.xlabel("Time (epoch unix timestamp)")
    plt.ylabel("Total coins in circulation")

    plt.show()

def difficulty(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    height = []
    difficulty = []

    for i, block in enumerate(blockchain.chain):
        height.append(block["height"])
        difficulty.append(int(block["target"], 16))


    plt.plot(height, difficulty)
    plt.title("Mining difficulty")
    plt.xlabel("Block")
    plt.ylabel("Difficulty")

    plt.show()

def block_time(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    height = []
    mining_time = []

    for i, block in enumerate(blockchain.chain):
        if i == 0:
            continue
        height.append(block["height"])
        mining_time.append(round(block["time"] - blockchain.chain[i-1]["time"]))


    #plt.plot(height, difficulty)
    plt.plot(height, mining_time)
    plt.title("Block time")
    plt.xlabel("Block")
    plt.ylabel("Block time (seconds)")

    plt.show()
