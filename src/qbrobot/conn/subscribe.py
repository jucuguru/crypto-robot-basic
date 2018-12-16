
########################################################################################################################
# subscription topics :
#  BASIC: 
#       ticker , candle, book , trade, instrument, 
#       order, account, account.position, account.margin, account.wallet, account.transact, account.execution, account.balance
#       create_order, cancel_order
#  CCXT:
#   ticker[fetch_ticker], candle[fetch_ohlcv], book[fetch_order_book], trade[fetch_trades], instrument[fetch_markets],
#   order[fetch_order/fetch_orders], account[fetch_balance], 
#   create_order[create_order], cancel_order[cancel_order]
#
#  bitmex websocket subscription: 
#   ticker[quote], candle[quoteBin1m], book[orderBookL2_25], trade[trade], instrument[instrument]
#   order[order], account.position[position], account.margin[margin], account.wallet[wallet], account.transact[transact], account.execution[execution],
#
#  bitmex http subscription:
#   ticker[/quote], candle[/quote/bucketed/binSize=1m], book[/orderBook/L2/depth=25], trade[/trade], instrument[/instrument/activeAndIndices]
#   order[/order], account.position[position], account.margin[margin], account.wallet[wallet], account.transact[transact], account.execution[execution],
#
#  bitfinex websocket subscription:
#    ticker[ticker], book[book], trade[trades], candle[candles] )
#    order[orders], account[accountinfo], account.position[positions], account.margin[margininfo], account.wallet[wallets], account.execution[trades], 
#      balacne[balacnceinfo], funding[fundinginfo]
#
#  bitfinex http subscription:
#    ticker[tickers?symbols=tBTCUSD,tETHUSD,fUSD], candle[candles/trade:1m:tBTCUSD/last], book[book/tBTCUSD/P0], trade[trades/tBTCUSD/hist], instrument[v1/symbols_details]
# 
########################################################################################################################
SUBSCRIPTION={
    'exchange':{
        'base':[
            'ticker', 'candle', 'book', 'trade', 'instrument', 
            'order', 'account', 'account.position', 'account.margin', 'account.wallet', 
            'account.transact', 'account.execution', 'account.balance',
        ],
        'ccxt':['ticker', 'candle', 'book', 'trade', 'instrument', 'order', 'account'],
        'bitmex':['ticker', 'candle', 'book', 'trade', 'instrument', 'order', 
                    'account.position', 'account.margin', 'account.wallet', 
                    'account.transact', 'account.execution', 'account.balance',],
        'bitfinex':['ticker', 'candle', 'book', 'trade', 'instrument', 'order', 
                    'account.position', 'account.margin', 'account.wallet', 
                    'account.transact', 'account.execution', 'account.balance'], 
        'bittrex':['ticker'],
        'kraken':['ticker'],
    },
    'altername':{
        'ccxt':{
            'ticker': 'fetch_ticker', 'candle': 'fetch_ohlcv', 'book': 'fetch_order_book', 
            'trade': 'fetch_trades', 'instrument': 'fetch_markets','order': 'fetch_order', 
            'account.balance': 'fetch_balance', 
        },
        'bitmex.websocket':{
            'ticker': 'quote', 'candle': 'quoteBin1m', 'book': 'orderBookL2_25', 
            'trade': 'trade', 'instrument': 'instrument', 'order': 'order', 
            'account.position': 'position', 'account.margin': 'margin', 
            'account.wallet': 'wallet', 'account.transact': 'transact', 'account.execution': 'execution', 
            },
        'bitmex.http':{
            'ticker': 'publicGetQuote', 'candle': 'publicGetQuoteBucketed', 'book': 'publicGetOrderBookL2', 
            'trade': 'publicGetTrade', 'instrument': 'publicGetInstrumentActiveAndIndices',
            'order': 'privateGetOrder', 'account.position': 'privateGetPosition', 'account.margin': 'margin', 
            'account.wallet': 'privateGetWallet', 'account.transact': 'privateGetTransact', 
            'account.execution': 'privateGetExecution', 
        },
        'bitfinex.websocket':{
            'ticker': 'ticker', 'book': 'book', 'trade': 'trades', 'candle': 'candles', 
            'order': 'orders', 'account': 'accountinfo', 'account.position': 'positions', 
            'account.margin': 'margininfo', 'account.wallet': 'wallets', 
            'balacne': 'balacnceinfo', 'funding': 'fundinginfo',
        },
        'bitfinex.http':{
            'ticker': 'publicGetTickersSymbols', 'candle': 'publicGetCandlesTrade1mLast', 
            'book': 'publicGetBookP0', 'trade': 'publicGetTradesHist', 'instrument': 'v1publicGetSymbolsDetails',
        },
        'bittrex':{},
        'kraken':{},
    },
    'type':{
        # 需要指定SYMBOL的主题
        'SYMBOL': [
            'ticker', 'candle', 'book', 'trade', 'instrument', 'order', 
                  ] ,
        # 无需指定SYMBOL的主题
        'GENERIC': [
            'account', 'account.position', 'account.margin', 'account.wallet', 
            'account.transact', 'account.execution', 'account.balance', 
        ],    
    },
    'auth':{
        'bitmex':[ 'order', 'account.position', 'account.margin', 'account.wallet', 
                    'account.transact', 'account.execution', 'account.balance',],
        'bitfinex':['order', 
                    'account.position', 'account.margin', 'account.wallet', 
                    'account.transact', 'account.execution', 'account.balance'],
        'kraken':[],
        'bittrex':[],
    },
}
