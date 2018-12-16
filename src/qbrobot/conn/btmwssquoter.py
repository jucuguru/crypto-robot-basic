#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

import logging

import time

## private import package

from qbrobot.util import log
from qbrobot.conn.connbase import Connector
from qbrobot.conn.bitmex_websocket import BitMEXWebsocket

#
# Helpers
#
logger = logging.getLogger()


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
            self.conn = BitMEXWebsocket( name = self.name, 
                                         exchange = self.exchange, 
                                         endpoint = self.baseurl, 
                                         symbol = self.symbol, 
                                         api_key = self.api_key, 
                                         api_secret= self.api_secret,
                                         data_q = self.q ,
                                         channels = self.channels )
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



