#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

import logging

import time
from threading import Thread
from multiprocessing import Queue

## private import package

from qbrobot import qsettings
from qbrobot.util import log
from qbrobot.conn.subscribe import SUBSCRIPTION
from qbrobot.conn.ccxtquoter import CCXTQuoterConnector
from qbrobot.conn.btmwssquoter import BitMEXWebsocketConnector
from qbrobot.conn.btfwssquoter import BitfinexWebsocketConnector

#
# Helpers
#
logger = logging.getLogger()



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
                    items =  self.__findConnectorByName( qsettings.CONNECTORS , item['backup'] )
                    for i in items :
                        if self.addConnector( item, api_key, data_q ):
                            logger.info( 'use backup connector %s, %s.'%( item['name'] , item['conntype']) )
                            status.append(True)
                else:
                    status.append( False )
                
        return all(status)


    def __findConnectorByName( self, connectors = None , connname = None):
        conns = []
        if connname and connectors:
            names = connname.split(',')
            for name in names:
                for c in connectors :
                    if c['name'] == name and c['type'] == 'backup' :
                        conns.append(c)
                        break
        return conns 


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
            _conn = self.__makeConnector( data_q , connParams, api_key, )
        else:
            _conn = self.__makeConnector( data_q , connParams, ) 
                                 
        if _conn : 
            self.connectors[ connParams['name'] ] = _conn 
            return True 
        else:
            return False


    def __makeConnector(self, data_q , params, api_key=None, ):
        """
            __makeConnector 创建链接， 
        Parameters:
            data_q -  数据队列，用于从connector接收到的数据，通过队列传递到 Robot 的主线程
            params - 链接所需的参数
                name -  connector's name and access key , examplse : "bmo_http", 
                exchange - connect to exchange id . now support : "bitmex", 'bitfinex', 'kraken'
                type -  链接类型， main 是主链接 ； backup是备份链接
                symbol -  some exchange's api need symbol, like "ETHUSD",
                conntype - connector type , support "http" or 'websocket',
                usage -   connector usage. "ORDER"--place order, and should auth; 'QUOTE'--only get data , private data should auth too.
                baseurl -  connector endpoint url . bitmex is "https://testnet.bitmex.com/api/v1/",
            api_key - 认证的key/sceret
        Returns:
            返回 True/False
        Raises:
            None
        """
        conntype = params['conntype'] if 'conntype' in params else ''
        exchange = params['exchange'] if 'exchange' in params else ''
        if conntype == 'http':
            conn = CCXTQuoterConnector( params, api_key, data_q )
        elif conntype == 'websocket':
            if exchange == 'bitmex':
                conn = BitMEXWebsocketConnector( params, api_key, data_q )
            elif exchange == 'bitfinex':
                conn = BitfinexWebsocketConnector( params, api_key, data_q )

        if conn and conn.connect():
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










