#!/usr/bin/env python3
"""
Wallet Tracker for token transactions across multiple EVM chains.
Uses Alchemy API for fetching transfers.
"""

import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from openpyxl import Workbook

load_dotenv()

WALLETS = [w.strip() for w in os.getenv("WALLETS", "").split(",") if w.strip()]
ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")

# Load config
with open("config.json") as f:
    config = json.load(f)

MAX_COUNT = config["max_count"]
TOKENS = config["tokens"]
CHAINS = config["chains"]

# Substitute ALCHEMY_KEY in RPC URLs
for chain in CHAINS.values():
    chain["rpc_url"] = chain["rpc_url"].replace("{ALCHEMY_KEY}", ALCHEMY_KEY)


def get_incoming_transfers(rpc_url: str, token_address: str, wallet: str) -> list:
    """Fetch all incoming token transfers using Alchemy API with pagination."""
    all_transfers = []
    page_key = None

    while True:
        params = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "toAddress": wallet,
            "contractAddresses": [token_address],
            "category": ["erc20"],
            "maxCount": hex(MAX_COUNT),
            "order": "desc",
        }
        if page_key:
            params["pageKey"] = page_key

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [params]
        }

        response = requests.post(rpc_url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise Exception(data["error"].get("message", "Unknown error"))

        result = data.get("result", {})
        transfers = result.get("transfers", [])
        all_transfers.extend(transfers)

        page_key = result.get("pageKey")
        if not page_key:
            break

    return all_transfers


def get_block_timestamp(rpc_url: str, block_hex: str) -> int:
    """Get block timestamp."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBlockByNumber",
        "params": [block_hex, False]
    }

    response = requests.post(rpc_url, json=payload, timeout=30)
    data = response.json()

    if "result" in data and data["result"]:
        return int(data["result"]["timestamp"], 16)
    return 0


def collect_transfers(chain: str, token_symbol: str, transfers: list, rpc_url: str, wallet: str) -> list:
    """Collect and process transfers for a chain/token pair."""
    token_config = TOKENS[token_symbol]
    min_amount = token_config["min_amount"]
    chain_name = CHAINS[chain]["name"]

    filtered = []
    for tx in transfers:
        if tx["value"] and tx["value"] >= min_amount:
            filtered.append({**tx, "chain": chain_name, "token": token_symbol, "wallet": wallet})

    # Get timestamps
    block_cache = {}
    for tx in filtered:
        block_hex = tx["blockNum"]
        if block_hex not in block_cache:
            block_cache[block_hex] = get_block_timestamp(rpc_url, block_hex)
        tx["timestamp"] = block_cache[block_hex]

    return filtered


def main():
    print(f"Wallet Tracker: {len(WALLETS)} wallet(s)")
    print(f"Fetching incoming transfers across {len(CHAINS)} chains...")

    all_txs = []

    for wallet in WALLETS:
        print(f"\nWallet: {wallet}")
        for chain, config in CHAINS.items():
            rpc_url = config["rpc_url"]

            for token_symbol, token_address in config["tokens"].items():
                try:
                    print(f"  Fetching {config['name']} {token_symbol}...")
                    incoming = get_incoming_transfers(rpc_url, token_address, wallet)
                    transfers = collect_transfers(chain, token_symbol, incoming, rpc_url, wallet)
                    all_txs.extend(transfers)
                    print(f"    Found {len(transfers)} transfers")
                except Exception as e:
                    print(f"    Error: {e}")

    # Sort by timestamp (oldest first)
    all_txs.sort(key=lambda x: x["timestamp"])

    # Group by year
    by_year = {}
    for tx in all_txs:
        year = datetime.fromtimestamp(tx["timestamp"]).year
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(tx)

    # Create Excel workbook
    print("\nGenerating Excel file...")
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    for year in sorted(by_year.keys()):
        ws = wb.create_sheet(title=str(year))
        ws.append(["Date", "Wallet", "Chain", "Token", "Amount", "From", "Hash", "Total_USDC"])
        total_usdc = 0.0
        for tx in by_year[year]:
            dt = datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            if tx["token"] in ("USDC", "USDC.e"):
                total_usdc += tx["value"]
            ws.append([dt, tx["wallet"], tx["chain"], tx["token"], round(tx["value"], 2), tx["from"], tx["hash"], round(total_usdc, 2)])
        print(f"  {year} ({len(by_year[year])} txs)")

    wb.save("out/transactions.xlsx")
    print(f"\nSaved to out/transactions.xlsx ({len(all_txs)} total transactions)")
    


if __name__ == "__main__":#
    main()
