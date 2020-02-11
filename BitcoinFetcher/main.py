from aiokafka import AIOKafkaProducer
from datetime import datetime

import aiomysql
import asyncio
import json
import logging
import os
import random
import signal
import sys
import time


class ProcessMetrics:
    def __init__(self, latest, limit):
        self.last_produced = latest
        self.num_tx = 0
        self.limit = limit
        self.kafka_producer = None
        self.conns = []


Q_MAX_SIZE = 10000
TX_Q_MAX_SIZE = 1000
KAFKA_Q_MAX_SIZE = 10000
NUM_WORKERS = 5
PRODUCER_COOLDOWN = 2
PRODUCER_SLEEP = 5
TX_PRODUCER_SLEEP = 2
TX_PRODUCER_COOLDOWN = 1
META_TOPIC = 'btc_tx_meta'
VIN_TOPIC = 'btc_vin'
VOUT_TOPIC = 'btc_vout'
BLOCK_TOPIC = 'btc_block'
BATCH_TIMEOUT = 10


async def run_command(cmd):
    # print(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        loop=loop)

    stdout, stderr = await proc.communicate()
    return [stdout, stderr]


async def run_bitcoin_cli_command(cmd):
    return await run_command('/usr/bin/bitcoin-cli -datadir=/home/ubuntu/data_disk/bitcoin ' + cmd)


async def main(metrics):
    metrics.kafka_producer = AIOKafkaProducer(
        loop=loop, bootstrap_servers=os.environ["KAFKA_SERVERS"])

    queue = asyncio.Queue(loop=loop)
    tx_queue = asyncio.Queue(loop=loop)

    k_block_queue = asyncio.Queue(loop=loop)
    k_meta_queue = asyncio.Queue(loop=loop)
    k_vin_queue = asyncio.Queue(loop=loop)
    k_vout_queue = asyncio.Queue(loop=loop)

    loop.create_task(height_producer(queue, metrics))
    loop.create_task(tx_generator(queue, tx_queue, metrics))

    for _ in range(NUM_WORKERS):
        loop.create_task(tx_fetcher(tx_queue, k_block_queue, k_meta_queue,
                                    k_vin_queue, k_vout_queue, metrics))

    loop.create_task(data_writer(BLOCK_TOPIC, k_block_queue, metrics))
    loop.create_task(data_writer(META_TOPIC, k_meta_queue, metrics))
    loop.create_task(data_writer(VIN_TOPIC, k_vin_queue, metrics))
    loop.create_task(data_writer(VOUT_TOPIC, k_vout_queue, metrics))


async def height_producer(queue, metrics):
    while metrics.limit >= metrics.last_produced:
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


def sql_row_transform(topic, payload):
    if topic == BLOCK_TOPIC:
        return (payload['hash'], payload['height'], payload['time'], payload['nTx'], payload['miner'], payload['rewards'])
    elif topic == VIN_TOPIC:
        return (payload['vin_txid'], payload['txid'], payload['vin_n'])
    elif topic == VOUT_TOPIC:
        return (payload['txid'], payload['val'], payload['addr'], payload['vout_n'])
    elif topic == META_TOPIC:
        return (payload['txid'], payload['blockhash'], payload['time'])
    else:
        return None


def sql_insert_transform(topic, cur, values):
    if topic == BLOCK_TOPIC:
        return cur.executemany("INSERT IGNORE INTO " + topic + " (hash, height, time, nTx, miner, rewards) values (%s,%s,%s,%s,%s,%s)", values)
    if topic == VIN_TOPIC:
        return cur.executemany("INSERT IGNORE INTO " + topic + " (vin_txid, txid, vin_n) values (%s,%s,%s)", values)
    if topic == VOUT_TOPIC:
        return cur.executemany("INSERT IGNORE INTO " + topic + " (txid, val, addr, vout_n) values (%s,%s,%s,%s)", values)
    if topic == META_TOPIC:
        return cur.executemany("INSERT IGNORE INTO " + topic + " (txid, blockhash, time) values (%s,%s,%s)", values)


async def data_writer(topic, queue, metrics):
    # write to both kafka & mysql
    # initialize kafka producer
    await metrics.kafka_producer.start()

    batch = metrics.kafka_producer.create_batch()
    most_recent = loop.time()
    conn = await aiomysql.connect(host=os.environ["MYSQL_HOST"], port=3306,
                                  user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWD"],
                                  db='bitcoin_database', loop=loop)
    metrics.conns.append(conn)

    values = []
    while True:
        payload = await queue.get()
        queue.task_done()
        #item = json.dumps({'schema': SCHEMA_MAP[topic], 'payload': payload})
        values.append(sql_row_transform(topic, payload))
        payload_json_str = json.dumps(payload)
        metadata = batch.append(
            key=None, value=payload_json_str.encode("utf-8"), timestamp=None)
        if metadata is None:
            # write to kafka
            partitions = await metrics.kafka_producer.partitions_for(topic)
            partition = random.choice(tuple(partitions))
            await metrics.kafka_producer.send_batch(batch, topic, partition=partition)
            print(
                f"{batch.record_count()} messages sent to partition {partition} of topic: {topic}")

            # write to mysql
            cur = await conn.cursor()
            await sql_insert_transform(topic, cur, values)
            await conn.commit()
            values.clear()
            cur = None

            # record current time
            most_recent = loop.time()
            # recreate a new batch
            batch = metrics.kafka_producer.create_batch()
        else:
            curr_time = loop.time()
            if (curr_time - most_recent > BATCH_TIMEOUT):
                # write to kafka
                partitions = await metrics.kafka_producer.partitions_for(topic)
                partition = random.choice(tuple(partitions))
                await metrics.kafka_producer.send_batch(batch, topic, partition=partition)
                batch = metrics.kafka_producer.create_batch()

                # write to mysql
                cur = await conn.cursor()
                await sql_insert_transform(topic, cur, values)
                await conn.commit()
                values.clear()
                cur = None


async def tx_fetcher(tx_queue, k_block_queue, k_meta_queue, k_vin_queue, k_vout_queue, metrics):
    while True:
        tx_info = await tx_queue.get()
        tx_queue.task_done()
        metrics.num_tx += 1
        tx_o, _ = await run_bitcoin_cli_command(f"getrawtransaction {tx_info['tx_id']} true")
        tx_json = json.loads(tx_o.decode().strip())
        vins = tx_json['vin']
        vouts = tx_json['vout']

        # process metadata
        k_meta_queue.put_nowait({
            'txid': tx_info['tx_id'],
            'blockhash': tx_json['blockhash'],
            'time': int(tx_json['time'])
        })

        # mining tx
        if len(vins) == 1 and ('coinbase' in vins[0].keys()):
            # process miner info
            for out in vouts:
                if 'addresses' in out['scriptPubKey']:
                    k_block_queue.put_nowait({
                        'hash': tx_json['blockhash'],
                        'height': int(tx_info['height']),
                        'time': int(tx_info['time']),
                        'nTx': int(tx_info['nTx']),
                        'miner': out['scriptPubKey']['addresses'][0],
                        'rewards': float(out['value'])
                    })
                break
            continue

        # non-mining tx
        # process vin
        for vin in vins:
            k_vin_queue.put_nowait({
                'vin_txid': vin['txid'],
                'txid': tx_info['tx_id'],
                'vin_n': int(vin['vout'])
            })

        # process vout
        for vout in vouts:
            is_non_standard = False if (
                'addresses' in vout['scriptPubKey'].keys()) else True
            k_vout_queue.put_nowait({
                'val': vout['value'],
                'txid': tx_info['tx_id'],
                'vout_n': int(vout['n']),
                'addr': 'nonstandard' if is_non_standard else vout['scriptPubKey']['addresses'][0]
            })


async def tx_generator(queue, tx_queue, metrics):
    while True:
        if tx_queue.qsize() > TX_Q_MAX_SIZE:
            print(
                f"[INFO] tx producer sleeps for {TX_PRODUCER_SLEEP} secs for workers to catch up")
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


async def shutdown(signal, metrics):
    logging.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks(loop=loop) if t is not
             asyncio.current_task(loop=loop)]

    for task in tasks:
        # skipping over shielded coro still does not help
        if task._coro.__name__ == "cant_stop_me":
            continue
        task.cancel()

    if metrics.kafka_producer:
        await metrics.kafka_producer.stop()
    for conn in metrics.conns:
        conn.close()

    logging.info("Cancelling outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True, loop=loop)
    loop.stop()

if __name__ == "__main__":
    latest = int(sys.argv[1])
    limit = 1000000
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    metrics = ProcessMetrics(latest, limit)
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, metrics)))

    try:
        start = time.time()
        loop.create_task(main(metrics))
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.stop()
        print('Caught SIGINT')
    finally:
        loop.close()

        end = time.time()
        print(
            f"Progress - last_produced_height: {metrics.last_produced}, num_tx_processed: {metrics.num_tx}, time_elapsed: {end - start}")
