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

# exchange API and ccxt
import  ccxt 


## private import package

from qbrobot import qsettings
from qbrobot.util import log
from qbrobot.conn.bitmex_websocket import BitMEXWebsocket
from qbrobot.conn.btfxwss import BtfxWss

#
# Helpers
#
logger = logging.getLogger()

# 
# Connector 负责管理一个链接
#
class Connector():

    def __init__(self, name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q ):
        self.q = data_q
        self.name = name 
        self.exchange = exchange
        self.symbol = symbol
        self.conntype = conntype
        self.usage = usage
        self.baseurl = baseurl
        self.api_key = api_key
        self.api_secret = api_secret

        self.subtopics = None
        if usage == 'QUOTE':
            self.subtopics = qsettings.SUBSCRIBE_TOPICS

        self.conn = None
        self.isconnected = False


    def connect(self):
        pass


    def run(self):
        pass

    def getConnector(self):
        return self.conn


    def reconnect(self):
        ret = self.connect()
        return ret 

    def disconnect( self ):
        self.isconnected = False
        logger.debug('Connector %s was disconnected...'%(self.name))


class QuoterConnector(Connector):
    """
        行情链接，需要保持长链接，所以有基本的ping和状态检查。
    """
    @staticmethod
    def extend(*args):
        if args is not None:
            result = None
            if type(args[0]) is collections.OrderedDict:
                result = collections.OrderedDict()
            else:
                result = {}
            for arg in args:
                result.update(arg)
            return result
        return {}


    def __ping(self):
        pass 

    def getstatus(self):
        pass


class TraderConnector(Connector):
    """
        交易链接，使用ccxt建立链接。
    """
    def __ping(self):
        pass 

    def getstatus(self):
        pass



class CCXTQuoterConnector(QuoterConnector):

    """
        ccxt的链接：无法找到定时ping的接口，暂时去掉。如果fetch数据出现 exception，则设置ping_status = False
    """
    def __ping(self):
        #while self.conntype == 'http'  and self.isconnected :
        #logger.debug(type(self.conn))
        if self.ping_status == False :
            try : 
                markets = self.conn.fetch_markets()
                if not markets :
                    self.ping_status = False
                    logger.warning( ( '%s Connector ping error...'%self.name ) )
                else:
                    self.ping_status = True
                    logger.info( '%s Connector  ping OK. markets first is %s %s '%(self.name, markets[0]['id'], markets[0]['price']) )
            except Exception as e:
                logger.info(( '%s Connector ping exception %s...'%( self.name, str(e) ) ) )
                self.ping_status = False

    def __pass_to_robot(self, channel, data ):
        logger.debug( "%s %s"%(channel, data ) )
        return self.q.put(( channel, data ))


    def __bitmex_fetch_instrument(self, requestparams = None ):
        """
            bitmex获取instrument合约信息. 获取其中的fundingRate, indicativeFundingRate
            对应——ccxt.bitmex.fetch_markets(),但ccxt api返回了所有合约和指数的信息，不需要这么多。
            param :
                requestparams HTTP Rest API 请求参数, 必须包含symbol
            return :
                True/False
        """
        ret = False
        try :
            if not requestparams :
                requestparams = {'symbol':self.symbol} 

            data = self.conn.publicGetInstrument( requestparams )
            if data:
                channel = (self.exchange , 'instrument', self.symbol ) 
                self.__pass_to_robot( channel , data )
                ret = True

        except Exception as e :
            logger.error(( '%s ccxt publicGetInstrument exception %s...'%( self.name, str(e) ) ) )
            self.ping_status = False

        return ret 



    def __bitmex_fetch_trade(self, requestparams = None ):
        """
            bitmex获取# ticker----lastprice ---? trader's price
            ccxt.bitmex.fetch_ticker(), 其中需要先fetch_markets(), 然后再 publicGetTradeBucket(), 得到TradeBin1m , 时效性太差
            用 publicGetTrade 返回的是当前时间最新的100笔交易数据
                "timestamp": "2018-08-28T00:00:08.716Z",
                "symbol": "ETHUSD",
                "side": "Buy",
                "size": 3000,
                "price": 288.3,
                "tickDirection": "ZeroPlusTick",
                "trdMatchID": "5c177c7b-9e95-c9bb-cafb-195b37142fd7",
                "grossValue": 86490000,
                "homeNotional": 20.721094073767095,
                "foreignNotional": 5973.891421467053
            param :
                requestparams HTTP Rest API 请求参数 必须包含symbol
            return :
                True/False
        """
        ret = False
        try :
            if not requestparams :
                requestparams = {'symbol':self.symbol} 

            data = self.conn.publicGetTrade(requestparams)
            if data and len( data ) :
                channel = (self.exchange , 'trade', self.symbol ) 
                self.__pass_to_robot( channel , data )
                ret = True 

        except Exception as e :
            logger.error(( '%s ccxt publicGetTrade exception %s...'%( self.name, str(e) ) ) )
            self.ping_status = False

        return ret 



    def __bitmex_fetch_orderbook(self, requestparams = None ):
        """
            bitmex获取# orderbook----bid,ask ---
            ccxt.bitmex.fetch_order_book(), 其中需要先fetch_markets(), 然后再 publicGetOrderBookL2(), 得到orderbook[25], 两次请求
            用 publicGetOrderBookL2(symbol), 返回当前时间的25个报价的side和size。Sell==ask, buy==bid
              {
                "symbol": "ETHUSD",
                "id": 29699998262,
                "side": "Sell",
                "size": 18803,
                "price": 86.9
              },
              {
                "symbol": "ETHUSD",
                "id": 29699998263,
                "side": "Buy",
                "size": 195471,
                "price": 86.85
              },
            param :
                requestparams HTTP Rest API 请求参数 必须包含symbol
            return :
                True/False
        """
        ret = False
        try :
            if not requestparams :
                requestparams = {'symbol':self.symbol, 'depth':10 } 

            data = self.conn.publicGetOrderBookL2( requestparams )
            logger.info( "orderBookL2 len [%d]"% (len(data) ) )
            if data and len(data):
                channel = (self.exchange , 'orderBookL2', self.symbol ) 
                self.__pass_to_robot( channel , data )
                ret = True 

        except Exception as e :
            logger.error(( '%s ccxt publicGetOrderBookL2 exception %s...'%( self.name, str(e) ) ) )
            self.ping_status = False

        return ret 


    def __bitfinex_fetch_ticker(self, requestparams = None ):
        """
            bitfinex 获取# ticker----lastprice ---? trader's price
            ccxt.bitfinex.fetch_ticker(), 其中需要先fetch_markets(), 然后再 publicGetPubtickerSymbol(), 得到ticker , 需要两次请求
            publicGetPubtickerSymbol 返回当前最新的价格等
                BID                 float   Price of last highest bid
                BID_SIZE            float   Sum of the 25 highest bid sizes
                ASK                 float   Price of last lowest ask
                ASK_SIZE            float   Sum of the 25 lowest ask sizes
                DAILY_CHANGE        float   Amount that the last price has changed since yesterday
                DAILY_CHANGE_PERC   float   Amount that the price has changed expressed in percentage terms
                LAST_PRICE          float   Price of the last trade
                VOLUME              float   Daily volume
                HIGH                float   Daily high
                LOW                 float   Daily low
            param :
                requestparams HTTP Rest API 请求参数 必须包含symbol
            return :
                True/False
        """
        ret = False
        try :
            if not requestparams :
                requestparams = {'symbol': ('t' + self.symbol ) } 

            data = self.conn.publicGetTickerSymbol(requestparams)
            if data and len(data):
                channel = (self.exchange , 'ticker', self.symbol ) 
                self.__pass_to_robot( channel , ( [data], time.time() )  )
                ret = True 

        except Exception as e :
            logger.error(( '%s ccxt publicGetPubtickerSymbol exception %s...'%( self.name, str(e) ) ) )
            self.ping_status = False

        return ret 


    def __bitfinex_fetch_orderbook(self, requestparams = None ):
        """
            bitfinex 获取# orderbook----bid,ask ---
            ccxt.bitfinex.fetch_order_book(), 其中需要先fetch_markets(), 然后再 publicGetBookSymbol(), 得到orderbook[25], 两次请求
            用 publicGetBookSymbolPrecision(symbol, Precision=P0), 返回当前时间的25个bids / asks 的pirce 和 size。
                PRICE   float   Price level
                COUNT   int Number of orders at that price level
                ±AMOUNT float   Total amount available at that price level.
                For Trading: if AMOUNT > 0 then bid else ask.
            param :
                requestparams HTTP Rest API 请求参数 必须包含symbol
            return :
                True/False
        """
        ret = False
        try :
            if not requestparams :
                requestparams = {'symbol':( 't' + self.symbol ), 'precision': 'R0' }
            else :
                requestparams['precision'] = 'P0'


            data = self.conn.publicGetBookSymbolPrecision(requestparams)
            if data and len(data):
                channel = (self.exchange , 'book', self.symbol ) 
                self.__pass_to_robot( channel , ( data, time.time() ) )
                ret = True 

        except Exception as e :
            logger.error(( '%s ccxt publicGetBookSymbol exception %s...'%( self.name, str(e) ) ) )
            self.ping_status = False

        return ret 



    def connect(self):
        """
            识别exchange和conntype，选择exchange api class 建立链接. 
            param :
                None
            return :
                True/False
        """
        if not self.conntype == 'http':
            logger.error( ('%s cannot use in ccxt qutoer connector.'%(self.conntype)) )
            return False

        logger.debug('Starting to create the connector %s %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))


        if self.exchange == 'bitmex':
                bitmex = ccxt.bitmex()
                bitmex.urls['api'] = self.baseurl
                if self.api_key and len( self.api_key) and self.api_secret and len(self.api_secret):
                    bitmex.apiKey = self.api_key
                    bitmex.secret = self.api_secret
                self.conn = bitmex
                # TODO 这里只是 把 链接对象准备好，但是还没有真正的使用，需要测试一下。ping/pong

        elif self.exchange == 'bitfinex': 
            #BITFINEX交易所1，用来交易
            if self.usage == 'ORDER':
                bitfinex1 = ccxt.bitfinex()
                if self.api_key and len( self.api_key) and self.api_secret and len(self.api_secret):
                    bitfinex1.apiKey = self.api_key
                    bitfinex1.secret = self.api_secret
                self.conn = bitfinex1

            elif self.usage == 'QUOTE':
                #BITFINEX交易所2，用来获取行情和账户信息
                bitfinex2 = ccxt.bitfinex2()
                if self.api_key and len( self.api_key) and self.api_secret and len(self.api_secret):
                    bitfinex2.apiKey = self.api_key
                    bitfinex2.secret = self.api_secret
                self.conn = bitfinex2

        elif self.exchange == 'kraken':
            #KRAKEN和BITTREX交易所，用来获取USDT对USD价格
            self.conn = ccxt.kraken()

        elif self.exchange == 'bittrex':
            #KRAKEN和BITTREX交易所，用来获取USDT对USD价格
            self.conn = ccxt.bittrex()

        else:
            logger.warning('Do not support exchange %s, please check the qsettings.py .'% self.exchange)

        # 建立链接正常，开始激活查询动作，并且开始轮训
        if self.conn :
            logger.debug('Created the connector %s %s %s %s %s %s...'%( 
                self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))
            self.isconnected = True
            self.ping_status = True

            # 启动运行程序
            t = Thread( target = self.run )
            t.daemon = True
            t.start()
            return True


    def getStatus(self ):
        logger.debug('http status check...')
        return (self.isconnected and self.ping_status)



    def run(self):
        """
            如果是 http 链接，需要建立长链接（keeplive），需要轮询保持 ping/pong 链接。

            ccxt的链接：

            bitmex的http链接：
                使用我们的批量委托 ，批量修改 ，和批量取消功能来减轻系统负担。批量操作可以更快地被执行。 批量取消操作，无论取消多少委托，都被计算为一次请求。
                如果账户的未执行交易订单过多且总值低于 0.0025 XBT ，则每个账户都会被标记为垃圾账户。
                保持 HTTP 连接和缓存的 SSL 会话。 如果你保持一个有效连接，我们保持活动状态的超时时间为90秒。
                BitMEX 交易引擎将在请求队列达到一定长度时开始卸载。 发生这种情况时，您将收到 503 状态码与消息 “系统当前超负荷， 请稍后再试。” 
                    请求不会到达交易引擎，您应该在至少 500 毫秒后重试。
        """
        logger.info('%s ccxt threading is started and running...'%(self.name)) 
        time_count = 0
        while self.conntype == 'http' and self.isconnected :

            try: 
                # TODO 调用接口开始查询数据query
                if self.exchange == 'bitmex' and self.ping_status:

                    symbol_dict = {'symbol':self.symbol} 
                    if not time_count % qsettings.INTERVAL_INSTR :
                        # 每60秒取一次instrument----fundingRate, indicativeFundingRate
                        self.__bitmex_fetch_instrument( requestparams = symbol_dict )

                    if not time_count % qsettings.INTERVAL_TICKER :
                        # 每三秒取一次ticker, ticker----lastprice ---? trader's price
                        self.__bitmex_fetch_trade( requestparams = symbol_dict )
                    
                    if not time_count % qsettings.INTERVAL_BOOK : 
                        # 每两秒取一次OrderBook, orderbook----bid,ask ---
                        self.__bitmex_fetch_orderbook( requestparams = symbol_dict )


                elif self.exchange == 'bitfinex' and self.ping_status:
                    # bitfinex 频率限制 每分钟60次，而且是按照IP地址和用户的总和，
                    symbol_dict = {'symbol':( 't' + self.symbol )} 

                    # 每三秒取一次ticker, ticker----lastprice 
                    if not time_count % qsettings.INTERVAL_TICKER :
                        self.__bitfinex_fetch_ticker(symbol_dict)

                    # 每两秒取一次OrderBook, orderbook----bid,ask ---
                    if not time_count % qsettings.INTERVAL_BOOK : 
                        self.__bitfinex_fetch_orderbook(symbol_dict)

                elif self.exchange == 'bittrex' and self.ping_status:
                    # 每三秒取一次ticker, ticker----lastprice 
                    if not time_count % qsettings.INTERVAL_TICKER :
                        data = self.conn.fetch_ticker('USDT/USD')
                        if data :
                            channel = (self.exchange , 'ticker', 'USDT/USD' ) 
                            self.__pass_to_robot( channel , data )

                elif self.exchange == 'kraken' and self.ping_status:
                    # 每三秒取一次ticker, ticker----lastprice 
                    if not time_count % qsettings.INTERVAL_TICKER :
                        data = self.conn.fetch_ticker('USDT/USD')
                        if data :
                            channel = (self.exchange , 'ticker', 'USDT/USD' ) 
                            self.__pass_to_robot( channel , data )

                self.ping_status = True

            except Exception as e:
                logger.error(( '%s ccxt fetch data exception %s...'%( self.name, str(e) ) ) )
                self.ping_status = False

            # __ping
            if not time_count % qsettings.INTERVAL_PING :
                self.__ping()

            time.sleep(qsettings.INTERVAL_QUOTER)
            if time_count == 300 :
                time_count = 0
            else:
                time_count += 1 

        return True


    def disconnect( self ):
        self.isconnected = False
        logger.info('Http Connector %s was disconnected...'%(self.name))




class BitfinexWebsocketConnector(Connector):
    """
      WebsocketConnector, 保持websocket长链接，提供稳定的实时链接。
        bitfinex 订阅数据后，返回的是队列，需要读取队列，然后集中写入到data_q， 传入后台。
    """
    def connect(self):
        """
            识别exchange和conntype，选择class 建立链接.  

            param :
                None
            return :
                True/False
        """
        if not self.conntype == 'websocket':
            logger.error( ('%s cannot use in websocket connector.'%(self.conntype)) )
            return False

        logger.debug('Starting to create the connector %s %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        if self.exchange == 'bitfinex':
            if self.api_key and self.api_secret and len( self.api_key ) and len( self.api_secret ) : 
                self.auth = True
                self.conn = BtfxWss( key = self.api_key, secret = self.api_secret )
            else:
                self.auth = False
                self.conn = BtfxWss( ) 
                #self.conn = BtfxWss( log_level = logging.DEBUG )

            self.conn.start()

        else:
            logger.warning('Do not support exchange %s, please check the qsettings.py .'% self.exchange)
            return False 

        # 建立链接，开始等待联通，并订阅信息
        if self.conn :

            # 等待链接到位
            while not self.conn.conn.connected.is_set():
                time.sleep(1)

            logger.debug('Created the connector OK %s %s %s %s %s %s...'%( 
                self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

            # Subscribe to some channels
            self.conn.subscribe_to_order_book(self.symbol)
            self.conn.subscribe_to_trades(self.symbol)
            self.conn.subscribe_to_ticker(self.symbol)
            # 如果没有登录 auth， 同时只能订阅三个channel
            #self.conn.subscribe_to_candles(pair = self.symbol, timeframe = '1m')

            time.sleep(1)

            self.ticker_q = self.conn.tickers(self.symbol)
            self.books_q = self.conn.books(self.symbol)
            self.trades_q = self.conn.trades(self.symbol)
            self.candles_q = self.conn.candles(self.symbol)
            self.account_q = self.conn.account

            self.isconnected = True
            self.run()
            return True
        else :
            return False


    def __pass_to_robot(self, channel, data ):
        logger.debug( "%s %s"%(channel, data ) )
        return self.q.put(( channel, data ))


    def __get_data_from_queue(self):
        """
            如果是 bitfinex 链接，定期轮询queue，并把数据传入后端
        """
        while self.exchange == 'bitfinex' and self.conntype == 'websocket'  and self.isconnected :
            channel = None
            data = None
            if not self.account_q.empty():
                data = self.account_q.get(timeout=0.1)
                channel = (self.exchange , 'account', self.symbol ) 
            
            if not self.ticker_q.empty():
                data = self.ticker_q.get(timeout=0.1)
                #logger.info("############get ticker :[%s]"%(str(data))  )
                channel = (self.exchange , 'ticker', self.symbol ) 
            
            if not self.books_q.empty():
                data = self.books_q.get(timeout=0.1)
                channel = (self.exchange , 'book', self.symbol ) 
            
            if not self.trades_q.empty():
                data = self.trades_q.get(timeout=0.1)
                channel = (self.exchange , 'trade', self.symbol ) 
            
            if not self.candles_q.empty():
                data = self.candles_q.get(timeout=0.1)
                channel = (self.exchange , 'candle', self.symbol ) 

            if channel and data:
                self.__pass_to_robot( channel , data )

            time.sleep(0.1)




    def run(self):
        """ 
            如果是 websocket链接，已经创建线程，Connector只是管理
            如果是 bitfinex 链接，定期轮询queue，并把数据传入后端
        """
        if self.conntype == 'websocket' and self.exchange == 'bitfinex' :

            logger.info('%s %s threading is started and running...'%(self.name, self.conntype))     

            # 如果是ORDER，需要循环心跳，keeplive，保持心跳和循环检查。。。
            t = Thread(target=self.__get_data_from_queue)
            t.daemon = True
            t.start()

        return True



    def reconnect(self):
        # TODO
        logger.debug('connector %s reconnect to  %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        conn_timeout = 5
        while not self.isconnected and conn_timeout : 
            ret = self.connect()
            time.sleep(2)
            conn_timeout -= 1 

        if not ret:
            logger.debug('connector %s reconnect is failed...  %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        return ret 

    def disconnect( self ):

        if self.conntype == 'websocket':
            '''
            # Unsubscribing from channels:
            try : 
                self.conn.unsubscribe_from_ticker(self.symbol)
                self.conn.unsubscribe_from_order_book(self.symbol)
                self.conn.unsubscribe_from_trades(self.symbol)
                self.conn.unsubscribe_from_candles(pair = self.symbol, timeframe = '1m')
            except:
                logger.exception('unsubscribe wrong')
            '''
            # Shutting down the client:
            self.conn.stop()

        self.isconnected = False
        logger.info('Websocket Connector %s was disconnected...'%(self.name))

    def getStatus(self ):
        logger.debug('websocket status check...')
        if not self.conn.conn.connected.is_set():
            logger.debug('websocket status exited')
            self.isconnected = False

        return (self.isconnected)




"""
class WSMHttpConnector(HttpConnector):
    # TODO WebSocket Mock HttpConnector  is backup for Websocket Connector
    # 通过http rest API（ccxt）模拟 websocket connector的订阅数据的功能
    # 把订阅数据功能改为主动轮询数据，返回的信息通过data_q返回到后台。
    def run(self):
        pass 
        #if self.conntype == 'http' and self.ping_status:
"""


class BitMEXWebsocketConnector(Connector):
    """
      WebsocketConnector, 保持websocket长链接，提供稳定的实时链接。
        bitmex，提供实时行情数据，以及账户数据，包括订单信息。 订阅数据后，bitmex主动推送数据，修改__on_message，集中写入到data_q， 传入后台。       
    """

    def connect(self):
        """
            识别exchange和conntype，选择class 建立链接. 
            param :
                None
            return :
                True/False
        """
        if not self.conntype == 'websocket':
            logger.error( ('%s cannot use in websocket connector.'%(self.conntype)) )
            return False

        logger.debug('Starting to create the connector %s %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        if self.exchange == 'bitmex':
            self.conn = BitMEXWebsocket( exchange = self.exchange, 
                                         endpoint = self.baseurl, 
                                         symbol = self.symbol, 
                                         api_key = self.api_key, 
                                         api_secret= self.api_secret,
                                         data_q = self.q ,
                                         subtopics = self.subtopics )
        else:
            logger.warning('Do not support exchange %s, please check the qsettings.py .'% self.exchange)

        if self.conn and not self.conn.exited:
            logger.debug('Created the connector OK %s %s %s %s %s %s...'%( 
                self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))
            self.isconnected = True
            return True
        else :
            return False


    def getStatus(self ):
        logger.debug('websocket status check...')
        if self.conn.exited:
            logger.debug('websocket status exited')
            self.isconnected = False

        if not self.conn.isReady :
            self.isconnected = False

        return (self.isconnected )


    def run(self):
        """
            如果是 websocket链接，已经创建线程，采用ws.run_forever 的模式，Connector只是管理
            如果是 http 链接，需要建立长链接（keeplive），需要轮询保持 ping/pong 链接。

            ccxt的链接：


            bitmex的http链接：
                使用我们的批量委托 ，批量修改 ，和批量取消功能来减轻系统负担。批量操作可以更快地被执行。 批量取消操作，无论取消多少委托，都被计算为一次请求。
                如果账户的未执行交易订单过多且总值低于 0.0025 XBT ，则每个账户都会被标记为垃圾账户。
                保持 HTTP 连接和缓存的 SSL 会话。 如果你保持一个有效连接，我们保持活动状态的超时时间为90秒。
                BitMEX 交易引擎将在请求队列达到一定长度时开始卸载。 发生这种情况时，您将收到 503 状态码与消息 “系统当前超负荷， 请稍后再试。” 
                    请求不会到达交易引擎，您应该在至少 500 毫秒后重试。
        """

        if self.conntype == 'websocket':
            #TODO 如果是行情数据，另写一个累，on_message写入queue。。。
            logger.info('%s websocket threading is started and running...'%(self.name))

        """
            while self.isconnected :
                # 如果是ORDER，需要循环心跳，keeplive，保持心跳和循环检查。。。
                t = Thread(target=echo_client, args=(q,))
                t.daemon = True
                t.start()
        """


    def reconnect(self):
        logger.debug('connector %s reconnect to  %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))
        conn_timeout = 5
        while not self.isconnected and conn_timeout : 
            ret = self.connect()
            time.sleep(1)
            conn_timeout -= 1 

        if not ret:
            logger.debug('connector %s reconnect is failed...  %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        return ret 

    def disconnect( self ):
        if self.conntype == 'websocket':
            self.conn.exit()

        self.isconnected = False
        logger.info('Websocket Connector %s was disconnected...'%(self.name))





class ConnectorManager(Thread):

    def __init__( self , data_q ):

        """
            __init__ 初始化链接管理器
        Parameters:
            data_q -  数据队列，用于从connector接收到的数据，通过队列传递到 Robot 的主线程
        Returns:
            None
        Raises:
            None
        """

        Thread.__init__(self)

        #atexit.register(self.exit)
        #signal.signal(signal.SIGTERM, self.exit)

        self.q = data_q 

        # 读取setting中的参数，创建所有的链接
        self.connectors = dict()

        if self.addAllConnector(data_q):
            if len(self.connectors) == len( qsettings.CONNECTORS ):
                self.status = 'healthy'
            else:
                self.status = 'warning'
        else:
            self.status = 'failed'
        
        if not self.status == 'failed':
            self.live = True
        else: 
            self.live = False

    def pollcheck(self):
        if not self.live :
            return 

        for name in self.connectors :
            c = self.connectors[name]
            if not c.getStatus() :
                if c.reconnect():
                    logger.debug('Connector %s have reconnected OK... '%(name))
                else :
                    self.status = 'warning'
                    logger.warning('Connector %s have disconnected, please check... '%(name))
            else:
                logger.info('Connector %s is normal...'%(name))



    def exit(self):

        # CM退出， 先置状态为 死掉，避免pollcheck
        self.live = False 

        for name in self.connectors:
            c = self.connectors[name]
            c.disconnect()
        self.status='disconnect'


    def addAllConnector(self, data_q ):
        """
            addConnector 创建链接， 并添加到 connector 字典容器中
        Parameters:
            data_q -  数据队列，用于从connector接收到的数据，通过队列传递到 Robot 的主线程
        Returns:
            返回 True/False
        Raises:
            None
        """
        status = []
        for item in qsettings.CONNECTORS:
            if item['type'] == 'backup':
                continue

            if item['auth']:
                api_key = qsettings.API_KEYS[ item['exchange'] ]
            else:
                api_key = None

            if self.addConnector( item, api_key, data_q ):
                logger.debug( 'add the %s connector successed.'% item['name'] )
                status.append(True)
            else:
                logger.warning( 'add the %s connector wrong. please checking.'% item['name'] )
                
                if item['backup'] and len(item['backup']) :
                    # 如果定义了备份链接，无法建立主链接，尝试备份链接(默认websocket无法链接，换成http)，只能退出。
                    item =  self.__findConnectorByName( qsettings.CONNECTORS , item['backup'] )
                    if self.addConnector( item, api_key, data_q ):
                        logger.info( 'use backup connector %s, %s.'%( item['name'] , item['conntype']) )
                        status.append(True)
                        continue

                status.append( False )
                
        return all(status)


    def __findConnectorByName( self, connectors , name ):
        conn = None
        if name and connectors:
            for c in connectors :
                if c['name'] == name :
                    conn = c
                    break
        return conn 


    def getConnectorByName(self, name ):
        """
            getConnectorByName 根据链接的名字获取链接， 返回链接前先检查链接是否可用，否则返回None
        Parameters:
            name -  链接的名称，在qsettings.py中定义
        Returns:
            conn - connector
        Raises:
            None
        """
        conn = self.connectors[name]
        if conn.getStatus():
            return conn
        else:
            return None


    def addConnector(self, connParams, api_key , data_q ):
        """
            addConnector 创建链接， 并添加到 connector 字典容器中
        Parameters:
            connParams - 链接参数 
            api_key - 链接密钥
            data_q -  数据队列，用于从connector接收到的数据，通过队列传递到 Robot 的主线程
        Returns:
            返回 True/False
        Raises:
            None
        """
        if api_key :
            _conn = self.__makeConnector( data_q , 
                                 connParams['name'], 
                                 connParams['exchange'], 
                                 connParams['symbol'], 
                                 connParams['conntype'], 
                                 connParams['usage'], 
                                 connParams['baseurl'],
                                 api_key['key'], 
                                 api_key['secret'], 
                                 )
        else:
            _conn = self.__makeConnector( data_q ,
                                 connParams['name'], 
                                 connParams['exchange'], 
                                 connParams['symbol'], 
                                 connParams['conntype'], 
                                 connParams['usage'], 
                                 connParams['baseurl'],
                                 )
        if _conn : 
            self.connectors[ connParams['name'] ] = _conn 
            return True 
        else:
            return False


    def __makeConnector(self, data_q , name, exchange, symbol, conntype, usage, baseurl, api_key=None, api_secret=None, ):
        """
            __makeConnector 创建链接， 
        Parameters:
            name -  connector's name and access key , examplse : "bmo_http", 
            exchange - connect to exchange id . now support : "bitmex", 'bitfinex', 'kraken'
            symbol -  some exchange's api need symbol, like "ETHUSD",
            conntype - connector type , support "http" or 'websocket',
            usage -   connector usage. "ORDER"--place order, and should auth; 'QUOTE'--only get data , private data should auth too.
            baseurl -  connector endpoint url . bitmex is "https://testnet.bitmex.com/api/v1/",
            data_q -  数据队列，用于从connector接收到的数据，通过队列传递到 Robot 的主线程
        Returns:
            返回 True/False
        Raises:
            None
        """
        if conntype == 'http':
            conn = CCXTQuoterConnector( name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q )
        elif conntype == 'websocket':
            if exchange == 'bitmex':
                conn = BitMEXWebsocketConnector( name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q )
            elif exchange == 'bitfinex':
                conn = BitfinexWebsocketConnector( name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q )

        if conn.connect():
            return conn
        else :
            return None


    def run(self):
        """
            ConnectorManager 维护和管理链接。负责每隔5秒轮询各个链接，读取链接的状态，如果有链接断开，就重连。
        Parameters:

        Returns:
            返回 True/False
        Raises:
            None
        """
        while not self.status == 'failed' and self.live :
            self.pollcheck()
            time.sleep(qsettings.INTERVAL_POLLCHECK)










