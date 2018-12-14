from os.path import join
import logging

########################################################################################################################
# Connection/Auth
########################################################################################################################
# 这里的symbol是用于创建链接，获取行情等信息用的
CONNECTORS = [
# Once you're ready, uncomment this.   

#    {   "name": "bm_ws_ethusd",
#        "type": "main",
#        "backup": 'bm_ccxt_ethusd', 
#        "exchange" : "bitmex",
#        "symbol": "ETHUSD",
#        "conntype"  : "websocket",
#        "usage"  : "QUOTE",
#        "baseurl": "https://www.bitmex.com",
#        "auth":False,   # public API 不需要认证
#        "subscribe":{
#            "SYMBOL_TOPICS":['ticker','orderBookL2_25', 'instrument', ],
#            "GENERIC_TOPICS":[],
#        },
#    },#
#    {   "name": "bm_ccxt_ethusd",
#        'type': 'backup',
#        #'type': 'main',
#        "backup": '', 
#        "exchange" : "bitmex",
#        "symbol": "ETHUSD",
#        "conntype"  : "http",
#        "usage"  : "QUOTE",
#        "baseurl": "https://www.bitmex.com",
#        "auth":False,   # public API 不需要认证
#        "subscribe":{
#            "SYMBOL_TOPICS":['ticker','orderBookL2', 'instrument', ],
#            "GENERIC_TOPICS":[],
#        },
#    },
#    {   "name"  : "bf_ws_ethusd", 
#        "type"  : "main",
#        "backup": 'bfq_ccxt_ethusd', 
#        "exchange" : "bitfinex",
#        "symbol": "ETHUSD",
#        "conntype"  : "websocket",
#        "usage"  : "QUOTE",
#        "baseurl": "wss://api.bitfinex.com/ws/2",
#        "auth":False,   # public API 不需要认证
#        "subscribe":{
#            "SYMBOL_TOPICS":['ticker','orderBookL2_25', 'instrument', ],
#            "GENERIC_TOPICS":[],
#        },
#    },
#    {   "name"  : "bf_ccxt_ethusd", 
#        "type"  : "backup",
#        #"type"  : "main",
#        "exchange" : "bitfinex",
#        "symbol": "ETHUSD",
#        "conntype"  : "http",
#        "usage"  : "QUOTE",
#        "baseurl": "https://api.bitfinex.com/ws/2",
#        "auth":False,   # public API 不需要认证
#        "subscribe":{
#            "SYMBOL_TOPICS":['ticker','books', 'trades', ],
#            "GENERIC_TOPICS":[],
#        },
#    },
    {   "name"  : "bf_ws_btcusdt", 
        #"type"  : "backup",
        "type"  : "main",
        "exchange" : "bitfinex",
        "symbol": "BTCUSD",  # mapping BTC/USDT
        "conntype"  : "websocket",
        "usage"  : "QUOTE",
        "baseurl": "https://api.bitfinex.com/ws/2",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker'],
            "GENERIC_TOPICS":[],
        },
    },
    {   "name"  : "bf_ccxt_btcusdt", 
        "type"  : "backup",
        #"type"  : "main",
        "exchange" : "bitfinex",
        "symbol": "BTCUSD",   # mapping BTC/USDT
        "conntype"  : "http",
        "usage"  : "QUOTE",
        "baseurl": "https://api.bitfinex.com/ws/2",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker', ],
            "GENERIC_TOPICS":[],
        },
    },
    {   "name"  : "bittrex_ccxt_usdt", 
        "type"  : "main",
        "exchange" : "bittrex",
        "symbol": "USDT/USD",
        "conntype"  : "http",
        "usage"  : "QUOTE",
        "baseurl": "",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker',],
            "GENERIC_TOPICS":[],
        },
    },
    {   "name"  : "kraken_ccxt_usdt", 
        "type"  : "main",
        "exchange" : "kraken",
        "symbol": "USDT/USD",
        "conntype"  : "http",
        "usage"  : "QUOTE",
        "baseurl": "",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker', ],
            "GENERIC_TOPICS":[],
        },
    },

#    {   "name"  : "bmq_ws_xbtusd", 
#        "exchange" : "bitmex",
#        "symbol": "XBTUSD",
#        "conntype"  : "websocket",
#        "usage"  : "QUOTE",
#        "baseurl": "https://testnet.bitmex.com",
#        "auth":T,   # public API 不需要认证
#        "subscribe":{
#            "SYMBOL_TOPICS":['ticker','orderBookL2_25', 'instrument', ],
#            "GENERIC_TOPICS":[],
#        },
#    },
]

# BASE_URL = "https://www.bitmex.com/api/v1/" 
# The BitMEX API requires permanent API keys. Go to https://testnet.bitmex.com/app/apiKeys to fill these out.
API_KEYS = {
# Once you're ready, uncomment this.
#        "bitmex": {
#            "key" : "1",
#            "secret" : "2",
#        },
#
#        "bitfinex": {
#            "key" : "3",
#            "secret" : "4",
#        },
#        "karen" : { 
#            "key" : "5",
#            "secret" : "6",
#        },
    "bitmex": {
        "key" : "Sk_rIPxkDrZRdCJDPrEsoCnl",
        "secret" : "Nhc-jBwAzl49zpVnvcZJYo3BicYRYCurCzR-znUEiXnoKk9M",
    },
    "bitfinex": {
        "key" : "",
        "secret" : "",
    },
    "karen" : { 
        "key" : "11",
        "secret" : "12",
    },
}



########################################################################################################################
# subscription topics  
# TOOD :
#   can only use for bitmex
#   bitfinex use channel ( account, book, order, trade, candles )
########################################################################################################################
SUBSCRIBE_TOPICS={
    # 需要指定SYMBOL的主题
    'SYMBOL_SUBSCRIBE_TOPICS': [
        # for bitmex
        "execution", "instrument", "order", "orderBookL2_25", "position", "quote", "quoteBin1m", "trade", "tradeBin1m",
        # for bitfinex
         'ticker', 'order', 'book', 'candle', 'account', 
    ] ,
    # 无需指定SYMBOL的主题
    'GENERIC_SUBSCRIBE_TOPICS': [
        # for bitmex
        "margin", "wallet", "transact", 
        # for bitfinex
        'account', 
    ],
}



########################################################################################################################
# LOG and MSG 
########################################################################################################################
dingding_robot_id = '3658359d9f465209e38933ec031b3c01df85e71820d627df5744377f90c09f74'

# Available levels: logging.(DEBUG|INFO|WARN|ERROR)
LOG_LEVEL = logging.INFO
LOG_FILE= '/tmp/quantrobot.log'
LOG_FORMATTER='%(asctime)s - %(levelname)s - %(threadName)s - %(filename)s - %(lineno)d - %(module)s - %(funcName)s - %(message)s'



########################################################################################################################
# INTERVAL for anything in QuoterServer
########################################################################################################################
# all INTERVAL 小于 5m， 300秒计数器归零。

INTERVAL_POLLCHECK = 155
INTERVAL_PING = 5
INTERVAL_QUOTER = 1
INTERVAL_INSTR = 60
INTERVAL_TICKER = 3 
INTERVAL_BOOK = 2 



########################################################################################################################
# Communication in the socket Quoter to Robot
########################################################################################################################
# Quoter Server receive the btc quote.
QuoterServer={
    'ip':'127.0.0.1',
    'port':'16666', 
}

# RobotServer wait for command to play/stop/pause/restart/exit
RobotServer={
    'ip':'127.0.0.1',
    'port':'26666',
}

# If any of these files (and this file) changes, reload the bot.
WATCHED_FILES = [join('qbrobot', 'qsettings.py')]


########################################################################################################################
# BitMEX Portfolio
########################################################################################################################

# Specify the contracts that you hold. These will be used in portfolio calculations.
CONTRACTS = ['XBTUSD']
