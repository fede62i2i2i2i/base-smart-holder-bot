import asyncio, time, json
from web3 import Web3
from telegram import Bot
from telegram.utils.request import Request

# Carica config
with open("config.json") as f: config = json.load(f)
with open("wallets.json") as f: wallets = json.load(f)

w3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
bot = Bot(token=config["telegram_token"], request=Request())

async def monitor():
    last_block = w3.eth.blockNumber
    seen = {}

    while True:
        try:
            block = w3.eth.getBlock("latest", full_transactions=True)
            for tx in block.transactions:
                if tx.to and tx.input and tx.value == 0:
                    token = tx.to
                    buyer = tx["from"]
                    if buyer in wallets:
                        seen.setdefault(token, []).append((buyer, block.timestamp, tx.input))
                        
            # Check for alerts
            for token, events in list(seen.items()):
                meat = events[-config["min_wallets"]:]
                buyers = {b for b, _, _ in meat}
                if len(buyers) >= config["min_wallets"]:
                    # Invia Telegram alert
                    lines = ["💸 New smart holder entry",
                             "",
                             f"🔎 Address: {token}",
                             f"🦚 {len(buyers)} smart holders"]
                    for b, ts, inp in meat:
                        name = wallets[b]
                        dt = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime(ts))
                        lines.append(f"🟢 {name} (${0:.0f}) ({dt})")
                    text = "\n".join(lines)
                    await bot.send_message(chat_id=config.get("telegram_chat_id"), text=text)
                    del seen[token]
        except Exception as e:
            print("Errore monitor:", e)

        await asyncio.sleep(config["check_interval_sec"])

async def main():
    await monitor()

if __name__ == "__main__":
    asyncio.run(main())
