from os.path import join
import logging

########################################################################################################################
# Connection/Auth
########################################################################################################################
# 这里的symbol是用于创建链接，获取行情等信息用的
CONNECTORS = [
# Once you're ready, uncomment this.   

    {   "name": "bmq_ws_ethusd",
        "type": "main",
        "backup": 'bmq_ccxt_ethusd', 
        "exchange" : "bitmex",
        "symbol": "ETHUSD",
        "conntype"  : "websocket",
        "usage"  : "QUOTE",
        "baseurl": "https://testnet.bitmex.com",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker','orderBookL2_25', 'instrument', ],
            "GENERIC_TOPICS":[],
        },
    },

    {   "name": "bmq_ccxt_ethusd",
        'type': 'backup',
        #'type': 'main',
        "backup": '', 
        "exchange" : "bitmex",
        "symbol": "ETHUSD",
        "conntype"  : "http",
        "usage"  : "QUOTE",
        "baseurl": "https://testnet.bitmex.com",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker','orderBookL2', 'instrument', ],
            "GENERIC_TOPICS":[],
        },
    },
    {   "name"  : "bfq_ws_btcusd2", 
        "type"  : "main",
        "backup": 'bfq_ccxt_btcusd2', 
        "exchange" : "bitfinex",
        "symbol": "BTCUSD",
        "conntype"  : "websocket",
        "usage"  : "QUOTE",
        "baseurl": "wss://api.bitfinex.com/ws/2",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker','orderBookL2_25', 'instrument', ],
            "GENERIC_TOPICS":[],
        },
    },
    {   "name"  : "bfq_ccxt_btcusd2", 
        "type"  : "backup",
        #"type"  : "main",
        "exchange" : "bitfinex",
        "symbol": "BTCUSD",
        "conntype"  : "http",
        "usage"  : "QUOTE",
        "baseurl": "https://api.bitfinex.com/ws/2",
        "auth":False,   # public API 不需要认证
        "subscribe":{
            "SYMBOL_TOPICS":['ticker','books', 'trades', ],
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
        "execution", "instrument", "order", "orderBookL2", "position", "quote", "quoteBin1m", "trade", "tradeBin1m",
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
# Order Size & Spread
########################################################################################################################

# How many pairs of buy/sell orders to keep open
ORDER_PAIRS = 6

# ORDER_START_SIZE will be the number of contracts submitted on level 1
# Number of contracts from level 1 to ORDER_PAIRS - 1 will follow the function
# [ORDER_START_SIZE + ORDER_STEP_SIZE (Level -1)]
ORDER_START_SIZE = 100
ORDER_STEP_SIZE = 100

# Distance between successive orders, as a percentage (example: 0.005 for 0.5%)
INTERVAL = 0.005

# Minimum spread to maintain, in percent, between asks & bids
MIN_SPREAD = 0.01

# If True, market-maker will place orders just inside the existing spread and work the interval % outwards,
# rather than starting in the middle and killing potentially profitable spreads.
MAINTAIN_SPREADS = True

# This number defines far much the price of an existing order can be from a desired order before it is amended.
# This is useful for avoiding unnecessary calls and maintaining your ratelimits.
#
# Further information:
# Each order is designed to be (INTERVAL*n)% away from the spread.
# If the spread changes and the order has moved outside its bound defined as
# abs((desired_order['price'] / order['price']) - 1) > settings.RELIST_INTERVAL)
# it will be resubmitted.
#
# 0.01 == 1%
RELIST_INTERVAL = 0.01


########################################################################################################################
# Trading Behavior
########################################################################################################################

# Position limits - set to True to activate. Values are in contracts.
# If you exceed a position limit, the bot will log and stop quoting that side.
CHECK_POSITION_LIMITS = False
MIN_POSITION = -10000
MAX_POSITION = 10000

# If True, will only send orders that rest in the book (ExecInst: ParticipateDoNotInitiate).
# Use to guarantee a maker rebate.
# However -- orders that would have matched immediately will instead cancel, and you may end up with
# unexpected delta. Be careful.
POST_ONLY = False

########################################################################################################################
# Misc Behavior, Technicals
########################################################################################################################

# If true, don't set up any orders, just say what we would do
# DRY_RUN = True
DRY_RUN = False

# How often to re-check and replace orders.
# Generally, it's safe to make this short because we're fetching from websockets. But if too many
# order amend/replaces are done, you may hit a ratelimit. If so, email BitMEX if you feel you need a higher limit.
LOOP_INTERVAL = 5

# Wait times between orders / errors
API_REST_INTERVAL = 1
API_ERROR_INTERVAL = 10
TIMEOUT = 7

# If we're doing a dry run, use these numbers for BTC balances
DRY_BTC = 50

# To uniquely identify orders placed by this bot, the bot sends a ClOrdID (Client order ID) that is attached
# to each order so its source can be identified. This keeps the market maker from cancelling orders that are
# manually placed, or orders placed by another bot.
#
# If you are running multiple bots on the same symbol, give them unique ORDERID_PREFIXes - otherwise they will
# cancel each others' orders.
# Max length is 13 characters.
ORDERID_PREFIX = "mm_bitmex_"

# If any of these files (and this file) changes, reload the bot.
WATCHED_FILES = [join('qbrobot', 'qsettings.py')]


########################################################################################################################
# BitMEX Portfolio
########################################################################################################################

# Specify the contracts that you hold. These will be used in portfolio calculations.
CONTRACTS = ['XBTUSD']
