*Block Data*:
hash (block hash) varchar(255) -- primary key + indexing
height int -- can also be used as primary key
time ?
nTx int
miner_addr varchar(255)
rewards int


*Transaction Meta Data*
txid varchar(255) -- primary key + indexing
blockhash varchar(255)
time ?

*vin_txid and txid* -- many to one
vin.txid varchar(256) -- not include coinbase -- primary key
txid varchar(256)
vin.vout int -- primary key

*vout address and transaction* --many to one
vout.value int
vout.scriptPubKey.address varchar(256)
vout.n int -- primary key
txid varchar(256) -- primary key

Given a certain wallet address, p1, how much does p1 get and when?
select val, time from Vout left join TxnMeta on Vout.txid = TxnMeta.txid where addr = 'p1';

Given a certain wallet address, p2, how much does p2 give away and when?
select val, time from Vout left join TxnMeta on Vout.txid = TxnMeta.txid 
where Vout.txid in 
(select txid from Vin where vin_id in 
(select txid from Vout where addr = 'p1'));




*Block Data*:
hash (block hash) 
--confirmations
--size
--weight
height
time
--mediantime
--chainwork
nTx
--previousblockhash
--nextblockhash
miner_addr
rewards


*Transaction Meta Data*
txid
--hash
--size
--vsize
--weight
blockhash
--confirmations
time 
--blocktime

*vin_txid and txid* -- many to one
vin.txid
txid
vin.vout
--vin.sequence

*vout address and transaction* --many to one
vout.value
vout.scriptPubKey.address
n
txid


{
  "txid": "908d0ed511aecd123defc8b904ad0a6dbaff2db92872cd60b26522a3e9d0279c",
  "hash": "908d0ed511aecd123defc8b904ad0a6dbaff2db92872cd60b26522a3e9d0279c",
  "version": 2,
  "size": 287,
  "vsize": 287,
  "weight": 1148,
  "locktime": 0,
  "vin": [
    {
      "txid": "061aa74186de02bf9201a696e1afa3ad36c66d35c84b68f37fdd72f538c5ffde",
      "vout": 3,
      "scriptSig": {
        "asm": "304402206b32d0c9499e992c53e70256ec0e069cde11f81118df4c3e6b422bb15ca7e0de02200c5d011610e459cfbf62672a1d3cafb46a26ff5fc3e5e6d6b4f1f923a3c702e2[ALL] 047146f0e0fcb3139947cf0beb870fe251930ca10d4545793d31033e801b5219abf56c11a3cf3406ca590e4c14b0dab749d20862b3adc4709153c280c2a78be10c",
        "hex": "47304402206b32d0c9499e992c53e70256ec0e069cde11f81118df4c3e6b422bb15ca7e0de02200c5d011610e459cfbf62672a1d3cafb46a26ff5fc3e5e6d6b4f1f923a3c702e20141047146f0e0fcb3139947cf0beb870fe251930ca10d4545793d31033e801b5219abf56c11a3cf3406ca590e4c14b0dab749d20862b3adc4709153c280c2a78be10c"
      },
      "sequence": 4294967295
    }
  ],
  "vout": [
    {
      "value": 0.11009846,
      "n": 0,
      "scriptPubKey": {
        "asm": "OP_HASH160 69f376fe18a39835d17e43ca037f969ff859b6fa OP_EQUAL",
        "hex": "a91469f376fe18a39835d17e43ca037f969ff859b6fa87",
        "reqSigs": 1,
        "type": "scripthash",
        "addresses": [
          "3BMEXvBrEXuZDFfCoh65sfPisfaYXiJLx6"
        ]
      }
    },
    {
      "value": 0.88983218,
      "n": 1,
      "scriptPubKey": {
        "asm": "OP_HASH160 6987488c7651399de29cd9fcdddc01dfd47ad413 OP_EQUAL",
        "hex": "a9146987488c7651399de29cd9fcdddc01dfd47ad41387",
        "reqSigs": 1,
        "type": "scripthash",
        "addresses": [
          "3BJzwLj3Na1Bg3TVP3gBCXaKogr92yxPFz"
        ]
      }
    },
    {
      "value": 4846.43724499,
      "n": 2,
      "scriptPubKey": {
        "asm": "OP_DUP OP_HASH160 43849383122ebb8a28268a89700c9f723663b5b8 OP_EQUALVERIFY OP_CHECKSIG",
        "hex": "76a91443849383122ebb8a28268a89700c9f723663b5b888ac",
        "reqSigs": 1,
        "type": "pubkeyhash",
        "addresses": [
          "17A16QmavnUfCW11DAApiJxp7ARnxN5pGX"
        ]
      }
    }
  ],
  "hex": "0200000001deffc538f572dd7ff3684bc8356dc636ada3afe196a60192bf02de8641a71a06030000008a47304402206b32d0c9499e992c53e70256ec0e069cde11f81118df4c3e6b422bb15ca7e0de02200c5d011610e459cfbf62672a1d3cafb46a26ff5fc3e5e6d6b4f1f923a3c702e20141047146f0e0fcb3139947cf0beb870fe251930ca10d4545793d31033e801b5219abf56c11a3cf3406ca590e4c14b0dab749d20862b3adc4709153c280c2a78be10cffffffff0336ffa7000000000017a91469f376fe18a39835d17e43ca037f969ff859b6fa87b2c64d050000000017a9146987488c7651399de29cd9fcdddc01dfd47ad41387d35c04d7700000001976a91443849383122ebb8a28268a89700c9f723663b5b888ac00000000",
  "blockhash": "0000000000000000000f79be8b80b8016a65813c52d0957697a9c2cc003f380d",
  "confirmations": 4,
  "time": 1580157265,
  "blocktime": 1580157265
}

{
  "txid": "7e2413898fdde81b4d0dfc4273d17ddc45f114f939b8a3556bd641b6fa656b5e",
  "hash": "96c79dbde27789f37193aef283545d5ceae1c7656d5187e06bbf8ec4efad176f",
  "version": 1,
  "size": 299,
  "vsize": 272,
  "weight": 1088,
  "locktime": 0,
  "vin": [
    {
      "coinbase": "038761091b4d696e656420627920416e74506f6f6c3432fd006f0020aa03b0ccfabe6d6d795efa36784d8d3dd6d7c6ef807391efa74d52463534d136d0731deee1dee127040000000000000084770000d3710000",
      "sequence": 4294967295
    }
  ],
  "vout": [
    {
      "value": 12.71849267,
      "n": 0,
      "scriptPubKey": {
        "asm": "OP_DUP OP_HASH160 11dbe48cc6b617f9c6adaf4d9ed5f625b1c7cb59 OP_EQUALVERIFY OP_CHECKSIG",
        "hex": "76a91411dbe48cc6b617f9c6adaf4d9ed5f625b1c7cb5988ac",
        "reqSigs": 1,
        "type": "pubkeyhash",
        "addresses": [
          "12dRugNcdxK39288NjcDV4GX7rMsKCGn6B"
        ]
      }
    },
    {
      "value": 0.00000000,
      "n": 1,
      "scriptPubKey": {
        "asm": "OP_RETURN aa21a9edf7a4a0d958b0544e11a340c98b117845f410a5505b8dbf0bcb2cd6fb593972b9",
        "hex": "6a24aa21a9edf7a4a0d958b0544e11a340c98b117845f410a5505b8dbf0bcb2cd6fb593972b9",
        "type": "nulldata"
      }
    },
    {
      "value": 0.00000000,
      "n": 2,
      "scriptPubKey": {
        "asm": "OP_RETURN b9e11b6d4213f573f7f34c181fd94d44a9e5f2a3b27c2bfb1deae4140b398a9666a3d439",
        "hex": "6a24b9e11b6d4213f573f7f34c181fd94d44a9e5f2a3b27c2bfb1deae4140b398a9666a3d439",
        "type": "nulldata"
      }
    }
  ],
  "hex": "010000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff54038761091b4d696e656420627920416e74506f6f6c3432fd006f0020aa03b0ccfabe6d6d795efa36784d8d3dd6d7c6ef807391efa74d52463534d136d0731deee1dee127040000000000000084770000d3710000ffffffff0333e1ce4b000000001976a91411dbe48cc6b617f9c6adaf4d9ed5f625b1c7cb5988ac0000000000000000266a24aa21a9edf7a4a0d958b0544e11a340c98b117845f410a5505b8dbf0bcb2cd6fb593972b90000000000000000266a24b9e11b6d4213f573f7f34c181fd94d44a9e5f2a3b27c2bfb1deae4140b398a9666a3d4390120000000000000000000000000000000000000000000000000000000000000000000000000",
  "blockhash": "0000000000000000000fd7d7d34ccf0cdeea2e2b468de431c88b330aab82c306",
  "confirmations": 18,
  "time": 1580146991,
  "blocktime": 1580146991
}

{
    "hash": "00000000e393fdeff24cd2633e59fe63e59c1fcde77a4faeeb8b3e052730d2c2",
    "confirmations": 478657,
    "strippedsize": 216,
    "size": 216,
    "weight": 864,
    "height": 16798,
    "version": 1,
    "versionHex": "00000001",
    "merkleroot": "5fc4e5a66657b44afb0d49c751fc8fe6500803434173788dc51e61d233526e05",
    "tx": [
        "5fc4e5a66657b44afb0d49c751fc8fe6500803434173788dc51e61d233526e05"
    ],
    "time": 1244611777,
    "mediantime": 1244609110,
    "nonce": 1760920119,
    "bits": "1d00ffff",
    "difficulty": 1,
    "chainwork": "0000000000000000000000000000000000000000000000000000419f419f419f",
    "nTx": 1,
    "previousblockhash": "00000000872de8ee1750e8847861e22f5a8ade93af7f58b2582b34bfa8642097",
    "nextblockhash": "000000008117782050b82b7d0bdef6686094f6d23acb65a3b519b4193f65d4fa"
}