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
from qbrobot.conn.connbase import QuoterConnector

#
# Helpers
#
logger = logging.getLogger()


class CCXTQuoterConnector(QuoterConnector):

    """
        ccxt的链接：无法找到定时ping的接口，暂时去掉。如果fetch数据出现 exception，则设置ping_status = False
    """
    def __ping(self):
        #while self.conntype == 'http'  and self.isconnected :
        #logger.debug(type(self.conn))
        if self.ping_status == False :
            try : 
                self.markets = self.conn.fetch_markets()
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


