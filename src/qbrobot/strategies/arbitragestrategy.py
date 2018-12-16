#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

import logging
import ssl
import json
import atexit
import signal
import time
from datetime import datetime
from threading import Thread, Event, Timer
from multiprocessing import Queue

import traceback

## private import package

from qbrobot import qsettings
from qbrobot.util import log
from qbrobot.strategy  import StrategyBase

#
# Helpers
#
logger = logging.getLogger()

# 
# 套利策略主类
#
class BMBFStrategy(StrategyBase):
    """
        套利策略，BM--Bitmex ， BF--Bitfinex ，在两个市场套利
    """
    def play(self):
        """
        运行的主体逻辑 
        """
        logger.info("BMBFStrategy start to play...")

        while self.getStatus() :
            
            symbol = 'ETHUSD'
            exchange='bitmex'
            table = 'trade'
            symbols = self.db.get_symbols(exchange, table)
            logger.info( " tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )

            timestamp, instrument = self.__bitmex_fetch_instrument(symbol)
            logger.debug("symbol - %s , instrument - %s", symbol, instrument)
            if instrument:
                logger.info("bitmex_fetch_funding_rate %s - %s - %s ", 
                        timestamp, instrument['fundingRate'], instrument['indicativeFundingRate']*0.3)
          

            timestamp, lastprice, trade = self.__bitmex_fetch_trade(symbol)
            logger.info("bitmex_fetch_lastprice %s %f %s"%(timestamp, lastprice, str(trade)))
          

            timestamp, bidprice, askprice, result = self.__bitmex_fetch_orderbook(symbol)
            logger.info("bitmex_fetch_orderbook - %s - %f - %f %s ", timestamp, bidprice, askprice, result)

            
            timestamp, ticker = self.__bitfinex_fetch_ticker(symbol)
            lastprice = ticker[-1]['last_price'] if ticker and len(ticker) and len(ticker[0]) > 6 else  0.0                 
            logger.info("bitfinex_fetch_ticker %s %s %f", symbol, timestamp , lastprice)
            
            timestamp, trade = self.__bitfinex_fetch_trade(symbol)
            lastprice = trade[-1]['price'] if trade and len(trade) else  0.0
            logger.info("bitfinex_fetch_trade %s %s %f %s", symbol, timestamp , lastprice, trade)

            timestamp, bidprice, askprice, result = self.__bitfinex_fetch_order_book(symbol)
            logger.info("__bitfinex_fetch_order_book %s %f %f.  result[%s] ", timestamp, bidprice, askprice , result )
            
            symbol = 'BTCUSD'
            timestamp, ticker = self.__bitfinex_fetch_ticker(symbol)
            lastprice = ticker[-1]['last_price'] if ticker and len(ticker) and len(ticker[0]) > 6  else 0.0
            logger.info("bitfinex_fetch_ticker %s %s %f", symbol, timestamp , lastprice)

            """
            symbol = 'USDT/USD'
            timestamp, ticker = self.__bittrex_fetch_ticker(symbol)
            lastprice = ticker['last'] if ticker else 0.0
            logger.info("bittrex_fetch_ticker %s %f"%(timestamp , lastprice))


            timestamp, ticker= self.__kraken_fetch_ticker(symbol)
            lastprice = ticker['last'] if ticker else 0.0
            logger.info("kraken_fetch_ticker %s %f"%(timestamp , lastprice))
            """

            time.sleep( qsettings.INTERVAL_STRATEGY*10)


    #TODO
    def profit(self):
        """
        运行的主体逻辑 
        """
        pass


    #TODO
    def getvalue(self):
        """
        运行的主体逻辑 
        """
        pass


    #
    # built-in functions 
    #

    def __bitmex_fetch_instrument( self, symbol ):
        """
            __bitmex_fetch_instrument 从 databoard 中读取最新的 symbol 合约中的 funding_rate
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, instrument
        Raises:
            None
        """
        timestamp = ''
        instrument = None

        exchange = 'bitmex'
        table = 'instrument'

        symbols = self.db.get_symbols(exchange, table)
        #logger.info( " tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )
        if symbols and symbol in symbols:
            data = self.db.get_data( exchange, table, symbol)
            logger.info("table - %s , symbol - %s , data - %s", table, symbol, str(data) )
            instrument = data[0] if data else None
            timestamp = instrument['timestamp']
            
        return ( timestamp, instrument )


    def __bitmex_fetch_trade( self, symbol ):
        """
            __bitmex_fetch_trade 从 databoard 中读取最新的 symbol trader 的 最新价 lastprice
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, lastprice
        Raises:
            None
        """
        timestamp = ''
        lastprice = 0.0
        trade = None

        exchange = 'bitmex'
        table = 'trade'

        symbols = self.db.get_symbols(exchange, table)
        if symbols and symbol in symbols:
            data = self.db.get_data( exchange, table, symbol)
            logger.info("table - %s , symbol - %s , data - %s", table, symbol, str(data) )
            trade = data[-1] if data else None
            if trade:
                lastprice = round( trade['price'] , 2 )
                timestamp = trade['timestamp']

        return ( timestamp, lastprice , trade )

    
    def __bitmex_fetch_orderbook( self, symbol ):
        """
            __bitmex_fetch_orderbook_bids 从 databoard 中读取最新的 symbol orderbook 中的 bids and ask
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, bidprice, askprice
        Raises:
            None
        """
        timestamp=''
        bidprice = 0.0
        askprice = 0.0

        result = {
            'bids': [],
            'asks': [],
            'timestamp': None,
            'datetime': None,
            'nonce': None,
        }

        exchange = 'bitmex'
        table = 'book'
        try :
            symbols = self.db.get_symbols(exchange, table)
            if symbols and symbol in symbols:
                data = self.db.get_data( exchange, table, symbol)
                            # [0] --price , [1]---amount
                result = data
                if len( result['bids'] ):
                    bidprice = result['bids'][0][0]
                if len( result['asks'] ):
                    askprice = result['asks'][0][0]

                logger.info("table - %s , symbol - %s , data - %s", table, symbol, str(data) )
                timestamp = result['timestamp']
                #logger.info( "333 orderbook bid %d , ask %d"%( bidprice , askprice ) )
        except Exception as e :
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )

        return ( timestamp, bidprice, askprice, result)

    
    def __bitfinex_fetch_ticker( self, symbol ):
        """
            __bitfinex_fetch_ticker 从 databoard 中读取最新的 symbol 合约中的 last_price
            ticker( (bid, bid size, ask, ask size, DAILY_CHANGE, DAILY_CHANGE_PERC, LAST_PRICE, VOLUME, HIGH, LOW), timestamp)
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, ticker
        Raises:
            None
        """
        ticker = None
        timestamp = ''

        exchange = 'bitfinex'
        table = 'ticker'

        try:
            symbols = self.db.get_symbols(exchange, table)
            #logger.info( "bitfinex tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )
            if symbols and symbol in symbols:
                data = self.db.get_data( exchange, table, symbol)
                #logger.info( "11111  ~%s~ ~%s~ " ,  data , symbol )
                if data:
                    ticker = data
                    timestamp = data[-1]['timestamp']
        except Exception as e :
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )

        return  (timestamp, ticker)

    
    def __bitfinex_fetch_trade( self, symbol ):
        """
            __bitfinex_fetch_trade 从 databoard 中读取最新的 symbol 合约中的 __bitfinex_fetch_trade
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, trade
        Raises:
            None
        """
        trade = None
        timestamp = ''

        exchange = 'bitfinex'
        table = 'trade'

        try:
            symbols = self.db.get_symbols(exchange, table)
            #logger.info( "bitfinex tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )
            if symbols and symbol in symbols:
                data = self.db.get_data( exchange, table, symbol)
                #logger.info( "11111  ~%s~ ~%s~ " ,  data , symbol )
                if data:
                    trade = data
                    timestamp = trade[-1]['timestamp']
        except Exception as e :
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )

        return  (timestamp, trade)

    
    def __bitfinex_fetch_order_book( self, symbol ):
        """
            __bitfinex_fetch_order_book 从 databoard 中读取最新的 symbol 合约中的 last_price
            book( [price, count, amount] )
                PRICE   float   Price level
                COUNT   int Number of orders at that price level
                ±AMOUNT float   Total amount available at that price level.
                For Trading: if AMOUNT > 0 then bid else ask.
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, ticker
        Raises:
            None
        """

        orderbook = None
        timestamp = ''
        bidprice = 0.0
        askprice = 0.0

        result = {
            'bids': [],
            'asks': [],
            'timestamp': None,
            'datetime': None,
            'nonce': None,
        }

        exchange = 'bitfinex'
        table = 'book'

        try:
                        
            symbols = self.db.get_symbols(exchange, table)
            
            if symbols and symbol in symbols:
                orderbook = self.db.get_data( exchange, table, symbol)

                result = orderbook
                if len( result['bids'] ):
                    bidprice = result['bids'][0][0]
                if len( result['asks'] ):
                    askprice = result['asks'][0][0]
                #logger.info("  %s %f %f .  result[%s] "%(timestamp, bidprice, askprice , result ))
                timestamp = result['timestamp']
        except Exception as e:
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )


        return (timestamp, bidprice, askprice, result)

    


    def __bittrex_fetch_ticker( self, symbol ):
        """
            __bittrex_fetch_ticker 从 databoard 中读取最新的 symbol 合约中的 last_price
            ticker={'symbol': 'USDT/USD', 'timestamp': 1544686658848, 'datetime': '2018-12-13T07:37:38.848Z', 
                'high': 0.9966, 'low': 0.9896, 'open': 0.9944, 'close': 0.993, 'last': 0.993, 
                'bid': 0.9921, 'bidVolume': None, 
                'ask': 0.9928, 'askVolume': None, 'vwap': 0.99319994, 'previousClose': None, 'change': None, 'percentage': None, 'average': None, 'baseVolume': 1720437.81782068, 'quoteVolume': 1708738.7374332305, 
                'info': {'a': ['0.99280000', '1972', '1972.000'], 'b': ['0.99210000', '986', '986.000'], 'c': ['0.99300000', '109.02023485'], 'v': ['199632.45901817', '1720437.81782068'], 'p': ['0.99350320', '0.99319994'], 't': [141, 1489], 'l': ['0.99190000', '0.98960000'], 'h': ['0.99480000', '0.99660000'], 'o': '0.99440000'}},
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, ticker
        Raises:
            None
        """
        ticker = None
        timestamp = ''

        exchange = 'bittrex'
        table = 'ticker'

        try:
            symbols = self.db.get_symbols(exchange, table)
            logger.info( "bittrex tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )
            if symbols and symbol in symbols:
                ticker = self.db.get_data( exchange, table, symbol)
                if ticker :
                    timestamp = ticker['datetime']

        except Exception as e :
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )

        return (timestamp, ticker)


    


    def __kraken_fetch_ticker( self, symbol ):
        """
            __kraken_fetch_ticker 从 databoard 中读取最新的 symbol 合约中的 last_price
            ticker={'symbol': 'USDT/USD', 'timestamp': 1544686658848, 'datetime': '2018-12-13T07:37:38.848Z', 
                'high': 0.9966, 'low': 0.9896, 'open': 0.9944, 'close': 0.993, 'last': 0.993, 
                'bid': 0.9921, 'bidVolume': None, 
                'ask': 0.9928, 'askVolume': None, 'vwap': 0.99319994, 'previousClose': None, 'change': None, 'percentage': None, 'average': None, 'baseVolume': 1720437.81782068, 'quoteVolume': 1708738.7374332305, 
                'info': {'a': ['0.99280000', '1972', '1972.000'], 'b': ['0.99210000', '986', '986.000'], 'c': ['0.99300000', '109.02023485'], 'v': ['199632.45901817', '1720437.81782068'], 'p': ['0.99350320', '0.99319994'], 't': [141, 1489], 'l': ['0.99190000', '0.98960000'], 'h': ['0.99480000', '0.99660000'], 'o': '0.99440000'}},
        Parameters:
            symbol - 指定合约的品种
        Returns:
            timestamp, ticker
        Raises:
            None
        """
        ticker = None
        timestamp = 0.0

        exchange = 'kraken'
        table = 'ticker'

        try:
            symbols = self.db.get_symbols(exchange, table)
            logger.info( "kraken tables %s , symbols %s" % (self.db.get_tables(exchange) , symbols ) )
            if symbols and symbol in symbols:
                ticker = self.db.get_data( exchange, table, symbol)
                if ticker :
                    timestamp = ticker['datetime']

        except Exception as e :
            logger.warning('%s wrongs %s'%(__class__.__name__, str(e) ) )

        return timestamp, ticker








