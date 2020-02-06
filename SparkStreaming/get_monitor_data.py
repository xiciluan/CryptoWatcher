from collections import defaultdict
from kafka import KafkaProducer
from kafka import SimpleProducer, KafkaClient
from pyspark.streaming.kafka import KafkaUtils
from pyspark.streaming import StreamingContext
from pyspark import SparkContex
from time import time

import json
import mysql.connector
import os
import sys


CHECKPOINT_PATH = '/dev/shm/spark'


def get_gini_index(sorted_list):
    '''
    Calculate gini index within the time window.
    - sorted_list: Ascending sorted list of total rewards given to different miners.
    return: Gini index.
    '''
    n = len(sorted_list)
    height = sum(val for val in sorted_list)
    area = sum((i+1)*val for i, val in enumerate(sorted_list))
    return round((2*area)/(n*height)-1-1/n, 2)


def get_max_hash_rate(sorted_list):
    '''
    Calculate max_hash_rate within the time window.
    - sorted_list: Ascending sorted list of total rewards given to different miners.
    return: Max hash rate.
    '''
    return round(sorted_list[-1]/sum(sorted_list), 2)


def write_to_mysql(result):
    '''
    - result: Tuple of result to be written to database. (time: int, gini_index: float, max_hash_rate: float)
    return: None. Results will be written to database.
    '''
    mydb = mysql.connector.connect(
        host=os.environ["MYSQL_HOST"],
        port=3306,
        user=os.environ["MYSQL_USER"],
        passwd=os.environ["MYSQL_PASSWD"],
        database="bitcoin_database"
    )
    mycursor = mydb.cursor()
    sql = "INSERT IGNORE INTO monitor_data (time, gini_index, max_hash_rate) VALUES (%s,%s, %s)"
    val = [result]
    mycursor.executemany(sql, val)
    mydb.commit()
    print(result, "was inserted.")


def handler(message):
    '''
    Define how to handle each RDD. 
    Specifically, first collect them and get sorted lists of values of total rewards given to 
    different miners. Then calculate decentralization indexs and write the result to database.
    - message: RDD of tuples (miner, sum_rewards) within the time window. 
    return None. Results will be written to database. 
    '''
    orig = message.collect()
    records = defaultdict(float)
    if len(orig) == 0:
        return
    for miner, val in orig:
        records[miner] += val
    vals = list(records.values())
    vals.sort()
    gini_index = get_gini_index(vals)
    max_hash_rate = get_max_hash_rate(vals)
    cur_time = int(time())
    result = (cur_time, gini_index, max_hash_rate)
    write_to_mysql(result)


def createContext():
    '''
    Create streaming Context.
    return streaming Context
    '''
    sc = SparkContext(appName="GetMonitorData")
    ssc = StreamingContext(sc, 20)

    kvs = KafkaUtils.createStream(
        ssc, zkQuorum, "spark-streaming-consumer", {topic: 1})
    lines = kvs.map(lambda x: x[1])
    groups = lines\
        .map(lambda x: json.loads(x))\
        .map(lambda x: (str(x['miner']), x['rewards']))\
        .reduceByKeyAndWindow(lambda x, y: x+y, lambda x, y: x-y, windowSize, slideSize)

    # groups.pprint()
    groups.foreachRDD(handler)

    ssc.checkpoint(CHECKPOINT_PATH)
    return ssc


if __name__ == '__main__':
    if len(sys.argv) != 5 and len(sys.argv) != 4:
        msg = ("Usage: get_monitor_data.py <hostname> <port> "
               "<window duration in seconds> [<slide duration in seconds>]")
        print(msg, file=sys.stderr)
        sys.exit(-1)
    zkQuorum, topic = sys.argv[1], sys.argv[2]
    windowSize = int(sys.argv[3])
    slideSize = int(sys.argv[4]) if (len(sys.argv) == 5) else windowSize

    context = StreamingContext.getOrCreate(CHECKPOINT_PATH, createContext)
    context.start()
    context.awaitTermination()
