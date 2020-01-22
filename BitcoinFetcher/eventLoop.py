#!/usr/bin/env python3

import asyncio
import datetime

import aiofiles as aiof
import json

LAST_BTC_BLK_ID = '/tmp/last_btc_block_id'
BTC_JSON_DIR = '/home/ubuntu/data_disk/btc_json'


async def run_command(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()
    return [stdout, stderr]


async def save_to_json(id, content):
    json_content = json.loads(content)
    json_str = json.dumps(json_content, indent=4)
    async with aiof.open(f"{BTC_JSON_DIR}/{id}.json", "w") as out:
        await out.write(json_str)
        await out.flush()
    print(f"done writing {id}.json")


async def run_bitcoin_cli_command(cmd):
    return await run_command('/usr/bin/bitcoin-cli -datadir=/home/ubuntu/data_disk/bitcoin ' + cmd)


async def scan_blocks_folder(loop, loc):
    current_block_id = -1
    while True:
        stdout, stderr = await run_bitcoin_cli_command('getblockchaininfo | jq .blocks')
        if (len(stderr.decode()) == 0):
            # no error
            current_block_id = int(stdout.decode())

        last_block_id = await fetch_last_block_id()
        if (current_block_id > last_block_id):
            to_process_block_id = last_block_id + 1
            print(
                f"have new block! last id: {last_block_id}, current: {current_block_id}, to process: {to_process_block_id}")
            hash_o, hash_e = await run_bitcoin_cli_command(f"getblockhash {to_process_block_id}")
            hash_str = hash_o.decode()
            json_o, json_e = await run_bitcoin_cli_command(f"getblock {hash_str}")
            await save_to_json(to_process_block_id, json_o.decode())
            await save_last_block_id(str(to_process_block_id))
        # await asyncio.sleep(1)


async def save_last_block_id(id):
    async with aiof.open(LAST_BTC_BLK_ID, "w") as out:
        await out.write(id)
        await out.flush()
    print("done saving last_block_id")


async def fetch_last_block_id():
    stdout, stderr = await run_command(f"cat {LAST_BTC_BLK_ID}")
    if (len(stderr.decode()) == 0):
        return int(stdout.decode())
    else:
        return -1

loop = asyncio.get_event_loop()

# Blocking call which returns when the display_date() coroutine is done
try:
    loop.run_until_complete(scan_blocks_folder(
        loop, '/home/ubuntu/data_disk/bitcoin/blocks'))
except KeyboardInterrupt:
    print('Caught Ctrl-C SIGINT, exiting...')
finally:
    loop.close()
