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

from time import sleep
from threading import Thread, Event, Timer
from multiprocessing import Queue

# exchange API and ccxt
from btfxwss import BtfxWss
import  ccxt 


## private import package

from qbrobot import settings
from qbrobot.util import log
from qbrobot.conn.bitmex_websocket import BitMEXWebsocket

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
            self.subtopics = settings.SUBSCRIBE_TOPICS

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




# 
# HttpConnector 负责管理一个HttpRest链接, 使用ccxt 建立链接
#
class HttpConnector(Connector):

    """
        ccxt的链接：定时ping，保证http链接是可用的
    """

    def __ping(self):
        while self.conntype == 'http'  and self.isconnected :
            #logger.debug(type(self.conn))
            balance = self.conn.fetch_balance()
            if not balance :
                self.ping_status = False
                logger.warning( ( '%s Connector ping error...'%self.name ) )
            else:
                self.ping_status = True
                logger.debug( '%s Connector  ping OK. balance is %s'%(self.name, balance['free']['BTC'] ) )
            sleep(5)


    def connect(self):
        """
            识别exchange和conntype，选择class 建立链接. 
            param :
                None
            return :
                True/False
        """
        logger.debug('Starting to create the connector %s %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        if not self.conntype == 'http':
            logger.error( ('%s cannot use in http connector.'%(self.conntype)) )
            return False

        if self.exchange == 'bitmex':
                bitmex = ccxt.bitmex()
                bitmex.urls['api'] = self.baseurl             
                bitmex.apiKey = self.api_key
                bitmex.secret = self.api_secret
                self.conn = bitmex
                # TODO 这里只是 把 链接对象准备好，但是还没有真正的使用，需要测试一下。ping/pong

        elif self.exchange == 'bitfinex': 
            #BITFINEX交易所1，用来交易
            if self.usage == 'ORDER':
                bitfinex1 = ccxt.bitfinex()
                bitfinex1.apiKey = ''
                bitfinex1.secret = ''
                self.conn = bitfinex1

            elif self.usage == 'QUOTE':
                #BITFINEX交易所2，用来获取行情和账户信息
                bitfinex2 = ccxt.bitfinex2()
                bitfinex2.apiKey = ''
                bitfinex2.secret = ''

        elif self.exchange == 'kraken':
            #KRAKEN和BITTREX交易所，用来获取USDT对USD价格
            self.conn = ccxt.kraken()

        elif self.exchange == 'bittrex':
            #KRAKEN和BITTREX交易所，用来获取USDT对USD价格
            self.conn = ccxt.bittrex()

        else:
            logger.warning('Do not support exchange %s, please check the settings.py .'% self.exchange)

        if self.conn :
            logger.debug('Created the connector %s %s %s %s %s %s...'%( 
                self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))
            self.isconnected = True
            self.ping_status = True
            self.run()
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
        if self.conntype == 'http' and self.ping_status :

            logger.info('%s http threading is started and running...'%(self.name))     

            # 如果是ORDER，需要循环心跳，keeplive，保持心跳和循环检查。。。
            t = Thread(target=self.__ping)
            t.daemon = True
            t.start()

        return True


    def disconnect( self ):
        self.isconnected = False
        logger.debug('Http Connector %s was disconnected...'%(self.name))




class WSMHttpConnector(HttpConnector):
    # TODO WebSocket Mock HttpConnector  is backup for Websocket Connector
    # 通过http rest API（ccxt）模拟 websocket connector的订阅数据的功能
    # 把订阅数据功能改为主动轮询数据，返回的信息通过data_q返回到后台。
    def run(self):
        pass 
        #if self.conntype == 'http' and self.ping_status:

class BitfinexWebsocketConnector(Connector):

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
            logger.warning('Do not support exchange %s, please check the settings.py .'% self.exchange)

        if self.conn and not self.conn.exited:
            logger.debug('Created the connector OK %s %s %s %s %s %s...'%( 
                self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))
            self.isconnected = True
            return True
        else :
            return False


class BitMEXWebsocketConnector(Connector):
    """
      WebsocketConnector, 保持websocket长链接，提供稳定的实时链接。
        bitmex，提供实时行情数据，以及账户数据，包括订单信息
        # TODO ————bitfinex，提供实时行情数据，以及账户数据，包括订单信息
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
            logger.warning('Do not support exchange %s, please check the settings.py .'% self.exchange)

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

        return (self.isconnected)


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
            sleep(1)
            conn_timeout -= 1 

        if not ret:
            logger.debug('connector %s reconnect is failed...  %s %s %s %s %s...'%( 
                    self.name, self.exchange, self.symbol, self.conntype, self.usage, self.baseurl))

        return ret 

    def disconnect( self ):
        if self.conntype == 'websocket':
            self.conn.exit()

        self.isconnected = False
        logger.debug('Websocket Connector %s was disconnected...'%(self.name))





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

        atexit.register(self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        self.q = data_q 

        # 读取setting中的参数，创建所有的链接
        self.connectors = dict()

        if self.addAllConnector(data_q):
            if len(self.connectors) == len( settings.CONNECTORS ):
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
                logger.debug('Connector %s is normal...'%(name))



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
        status = True
        for item in settings.CONNECTORS:
            api_key = settings.API_KEYS[ item['exchange'] ]
            if self.addConnector( item, api_key, data_q ):
                logger.debug( 'add the %s connector successed.'% item['name'] )
            else:
                logger.warning( 'add the %s connector wrong. please checking.'% item['name'] )
                """
                if item['exchange'] in [ 'bitmex', 'bitfinex' ]:
                    # 如果是主要交易所，无法建立链接，尝试备份链接(默认websocket无法链接，换成http)，只能退出。
                    if item['conntype'] == 'websocket':
                        item['conntype'] = 'http'
                        if self.addConnector( item, api_key, data_q ):
                            logger.warning( 'use backup connector %s, %s.'%( item['name'] , item['conntype']) )
                        else :
                            status = False
                            break
                    elif item['usage'] == 'ORDER':
                        status = False
                        break
                    else :
                        item['conntype'] = 'websocket'
                        if self.addConnector( item, api_key, data_q ):
                            logger.warning( 'use backup connector %s, %s.'%( item['name'] , item['conntype']) )
                        else :
                            status = False
                            break
                """
                status = False
                break
                

        return status

    def getConnectorByName(self, name ):
        """
            getConnectorByName 根据链接的名字获取链接， 返回链接前先检查链接是否可用，否则返回None
        Parameters:
            name -  链接的名称，在settings.py中定义
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
        _conn = self.__makeConnector( connParams['name'], 
                                 connParams['exchange'], 
                                 connParams['symbol'], 
                                 connParams['conntype'], 
                                 connParams['usage'], 
                                 connParams['baseurl'],
                                 api_key['key'], 
                                 api_key['secret'], 
                                 data_q )
        if _conn : 
            self.connectors[ connParams['name'] ] = _conn 
            return True 
        else:
            return False


    def __makeConnector(self, name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q ):
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
            conn = HttpConnector( name, exchange, symbol, conntype, usage, baseurl, api_key, api_secret , data_q )
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
            sleep(15)









