import asyncio
import random
import sys
from datetime import datetime
import json


class ProcessMetrics:
    def __init__(self, latest):
        self.works = latest
        self.last_produced = latest


Q_MAX_SIZE = 300
TX_Q_MAX_SIZE = 1000
NUM_WORKERS = 5
PRODUCER_COOLDOWN = 2
PRODUCER_SLEEP = 5
TX_PRODUCER_SLEEP = 2
TX_PRODUCER_COOLDOWN = 1


async def run_command(cmd):
    # print(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()
    return [stdout, stderr]


async def run_bitcoin_cli_command(cmd):
    return await run_command('/usr/bin/bitcoin-cli -datadir=/home/ubuntu/data_disk/bitcoin ' + cmd)


async def main(metrics):
    queue = asyncio.Queue()
    tx_queue = asyncio.Queue()
    hp = [asyncio.create_task(
        height_producer(queue, metrics))]

    tg = [asyncio.create_task(tx_generator(queue, tx_queue, metrics))]

    workers = []
    for _ in range(NUM_WORKERS):
        worker = asyncio.create_task(
            tx_fetcher(tx_queue, metrics))
        workers.append(worker)

    await asyncio.gather(*hp, return_exceptions=True)
    await asyncio.gather(*tg, return_exceptions=True)
    await asyncio.gather(*workers, return_exceptions=True)


async def height_producer(queue, metrics):
    while True:
        if queue.qsize() > Q_MAX_SIZE:
            print(
                f"[INFO] producer sleeps for {PRODUCER_SLEEP} secs for workers to catch up")
            await asyncio.sleep(PRODUCER_SLEEP)
            print(f"[INFO] producer awakes")
            continue

        stdout, stderr = await run_bitcoin_cli_command('getblockchaininfo | jq .blocks')
        if (len(stderr.decode()) == 0):
            # no error
            current_block_id = int(stdout.decode())
            diff = current_block_id - metrics.last_produced
            print(f"[INFO] current block height {current_block_id}")
            num_items_to_put = Q_MAX_SIZE if diff > Q_MAX_SIZE else diff

            last_produced = metrics.last_produced
            for block in range(last_produced+1, last_produced+num_items_to_put+1):
                queue.put_nowait(block)
                metrics.last_produced = block

            print(f"[INFO] produced up to {metrics.last_produced}")
        await asyncio.sleep(PRODUCER_COOLDOWN)


async def write_to_kafka(topic, schema, content):
    if (topic == 'btc_vins' or topic == 'btc_vouts'):
        print(f"topic: {topic}, content: {content}")


async def tx_fetcher(tx_queue, metrics):
    while True:
        tx_info = await tx_queue.get()
        tx_queue.task_done()
        tx_o, _ = await run_bitcoin_cli_command(f"getrawtransaction {tx_info['tx_id']} true")
        tx_json = json.loads(tx_o.decode().strip())
        vins = tx_json['vin']
        vouts = tx_json['vout']

        # process metadata
        asyncio.create_task(write_to_kafka('btc_tx_meta', {}, {
            'txid': tx_info['tx_id'],
            'blockhash': tx_json['blockhash'],
            'time': tx_json['time']
        }))

        # mining tx
        if len(vins) == 1 and ('coinbase' in vins[0].keys()):
            # process miner info
            for out in vouts:
                if 'addresses' in out['scriptPubKey']:
                    asyncio.create_task(write_to_kafka('btc_blocks', {}, {
                        'hash': tx_json['blockhash'],
                        'height': tx_info['height'],
                        'time': tx_info['time'],
                        'nTx': tx_info['nTx'],
                        'miner': out['scriptPubKey']['addresses'][0],
                        'rewards': out['value']
                    }))
                break
            continue

        # non-mining tx
        # process vin
        for vin in vins:
            asyncio.create_task(write_to_kafka('btc_vins', {}, {
                'vin.txid': vin['txid'],
                'txid': tx_info['tx_id'],
                'vin.vout': vin['vout']
            }))

        # process vout
        for vout in vouts:
            is_non_standard = False if (
                'addresses' in vout['scriptPubKey'].keys()) else True
            asyncio.create_task(write_to_kafka('btc_vouts', {}, {
                'vout.value': vout['value'],
                'txid': tx_info['tx_id'],
                'vout.n': vout['n'],
                'vout.scriptPubKey.address': 'nonstandard' if is_non_standard else vout['scriptPubKey']['addresses'][0]
            }))


async def tx_generator(queue, tx_queue, metrics):
    while True:
        if tx_queue.qsize() > TX_Q_MAX_SIZE:
            print(
                f"[INFO] tx producer sleeps for {PRODUCER_SLEEP} secs for workers to catch up")
            await asyncio.sleep(TX_PRODUCER_SLEEP)
            print(f"[INFO] tx producer awakes")
            continue
        item = await queue.get()
        queue.task_done()

        hash_o, _ = await run_bitcoin_cli_command(f"getblockhash {item}")
        hash_str = hash_o.decode().strip()
        block_o, _ = await run_bitcoin_cli_command(f"getblock {hash_str}")

        block_json = json.loads(block_o.decode().strip())
        txs = block_json['tx']
        for tx_id in txs:
            data = {'nTx': block_json['nTx'], 'height': block_json['height'],
                    'time': block_json['time'], 'tx_id': tx_id}
            tx_queue.put_nowait(data)

        # print(
        #    f"[INFO] produced {block_json['nTx']} tx on height: {item}, block time: {block_json['time']}")
        metrics.works = item

if __name__ == "__main__":
    latest = int(sys.argv[1])
    metrics = ProcessMetrics(latest)
    try:
        asyncio.run(main(metrics))
    except KeyboardInterrupt:
        print(f"SIGINT received, exiting...")
        print(f"current progress: {metrics.works}")
