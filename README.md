# Wallet Tracker

Track token transactions across multiple EVM chains using Alchemy API.

## Supported Chains

- Ethereum
- Polygon
- Optimism
- Base
- Arbitrum
- zkSync

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your credentials:
   ```
   WALLETS=0xWallet1,0xWallet2,0xWallet3
   ALCHEMY_KEY=YourAlchemyApiKey
   ```

4. Optionally edit `config.json` to customize chains, tokens, and `max_count`, which is the maximum number of txs fetched from Alchemy for each chain.

## Usage

```bash
python3 wallet-tracker.py
```

The script generates `out/transactions.xlsx` with a sheet for each year of incoming transactions:
- `2022`
- `2023`
- etc.
