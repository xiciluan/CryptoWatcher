# CryptoWatcher

An End-to-end Real-time Bitcoin Monitoring System.

[www.artofdata.me](http://www.artofdata.me) to website.

[github.com/xiciluan/CryptoWatcher-www](https://github.com/xiciluan/CryptoWatcher-www) to frontend & backend github repo.

[bit.ly/xici-crypto-watcher](https://bit.ly/xici-crypto-watcher) to presentation slides.


## Introduction
What is blockchain? The whole bitcoin blockchain is like a giant ledger containing all the transaction history in bitcoin. Roughly every 10 minutes, it gets updated as an additional “block” of new transactions is permanently added to the ledger. Everyone can have their own copy of the ledger. It’s completely transparent.

So, who updates this ledger? In blockchain’s world, the one who first solve a complex computational problem takes this role. Now the problem comes: what if someone's computational power is so large (centralized power) that he or she can even manipulate the ledger? For instance, in May 2018, Bitcoin Gold was hit by a 51% hashing attack (> 51% of computational power) by an unknown actor, enabling him to make false update to the ledger and spend the same digital coins more than once. 

We definitely want to avoid such problem to maintain the overal health of the bitcoin blockchain. In this monitoring system, we provide live blockchain data monitoring (monitoring incoming blocks and calculating the decentralization indexes of the most recent time windows). Moreover, we create a query builder for on-demand extraction and visualization of historical data.

## Architecture
![pipeline](https://github.com/xiciluan/CryptoWatcher/blob/master/Image/pipeline.png)
Firstly, the raw blockchain binary data is downloaded to a ec2 instance from peer-to-peer network.
The binary data is then parsed into human-readable format using RPC that comes with the blockchain daemon and sent to kafka cluster. There are 3 kafka consumers in this pipeline.

1. The parsed data will be directly saved to database for future query and analysis.
   
2. The data will be piped to SparkStreaming so as to calculate the decentralization index and max hash rate based on the data within the previous 1 hour time window. The backend server can fetch historical data from the database.
   
3. The real-time data will also be directly sent to Node.js backend server to guarantee that the latency between data fetching and display is minimized. Specifically, the latency is less than 180 ms (50 ms UI animation time included).
   
Finally, I use node.js with GraphQL as backend server for reduce the number of API endpoints and maximize the flexibility on the front-end, which is based on React. 


## Engineering Challenge
### Engineering Challenge #1 - Effective Data Retrieval & Parsing
The process of getting real-time and human-readable blockchain data with transaction details is quite complicated. Basically, the process is as follows. 
![parsing_process](https://github.com/xiciluan/CryptoWatcher/blob/master/Image/parsing_process.png)

1. Long-running bitcoin daemon (`bitcoind`) to get the latest blockchain raw binary data. 
   
2. Parse the data with json RPC that comes with the blockchain daemon and get the current block height; that is, the number of blocks that have been mined till now.
   
3. Generate a list of height representing the data of blocks that we haven’t parsed. For instance, if the current height is 1000 and we have 500 blocks’ data being successfully parsed, then the height we generate should be from 501 to 1000. 
   
4. For each height, it can be parsed into a unique block hash by calling `bitcoin-cli getblockhash`.
   
5. By parsing on each block hash by calling `bitcoin-cli getblock`, we can get the detailed information related to it including a long list of transaction id; that is, the id of transactions that have been confirmed in this block. 
   
6. Then we need to parse each transaction id and get its details by calling `bitcoin-cli getrawtransaction`. 
   
7. Finally, we extract the information from transatcion details and write it to different kafka topics.
   
![time_efficiency](https://github.com/xiciluan/CryptoWatcher/blob/master/Image/time_efficiency.png) 
The process is already quite complicated. A major bottleneck for improving time efficiency for data processing is that the raw data is stored in the hard drive and it takes millions of cycles to fetch it. According to [Jeff Dean's latency table](https://gist.github.com/jboner/2841832), assuming each cycle takes one nano second, reading 1 megabyte from hard drive takes more than 20 million cycles. So it is better to make good use of this I/O wait time. Therefore, I apply AsyncIO library in Python 3.7 to eliminate I/O wait time. According to my benchmark, the number of transactions being processed increased about 95% on a single thread, which greatly improves the time efficiency for data processing. 


### Engineering Challenge #2 - Improving System Scalability
![parsing_pipeline](https://github.com/xiciluan/CryptoWatcher/blob/master/Image/parsing_pipeline.png)
The bitcoin raw data is already over 500GB (over 5 TB after parsing). In reality, there are a lot more different types of cryptocurrencies. Therefore, to make the process can be easily scaled, I apply this whole structure for data retrieval and parsing. 

Basically, I add a queue between each two process so different workers just retrieve a task from a queue and output the result to different queues. They don’t have any internal states. Therefore, this horizontally scaling methodology can be easily converted into industry grade project, like replacing each queue with a MQ system or message broker and each worker with a complete system since different parts are actually stateless and what they do is just their own work.


## Contact
Xici Luan: xiciluan@gmail.com
