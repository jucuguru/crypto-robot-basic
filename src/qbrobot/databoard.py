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


## private import package

from qbrobot import settings
from qbrobot.util import log

#
# Helpers
#
logger = logging.getLogger()

# 
# DataBoard 负责从data_q读取数据，并维护数据面板
#
class DataBoard(Thread):

    def __init__( self , data_q ):
        """
            __init__ 初始化数据面板管理器
        Parameters:
            data_q -  数据队列，用于从connector接收数据
        Returns:
            None
        Raises:
            None
        """

        Thread.__init__(self)

        atexit.register(self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        self.q = data_q 


        # 存放数据的空间 —— 用字典存放 , 按照channel存放 channel = ( exchange, table, symbol ) 
        # 第一层是 exchange(), 第二层是 table
        #
        self.datastore = dict()

        # 定义状态
        self.live = True
        self.ready = False



    def get_data( self, exchange, table, symbol=None):
        """
            read_data 从data_q中读取数据
        Parameters:
            data_q -  数据队列，用于从connector接收数据
        Returns:
            None
        Raises:
            None
        """
        if exchange in self.datastore :
            if table in self.datastore[exchange]:
                if table in settings.SUBSCRIBE_TOPICS['GENERIC_SUBSCRIBE_TOPICS'] :
                    return self.datastore[exchange][table]
                else :
                    if symbol in self.datastore[exchange][table]:
                        return self.datastore[exchange][table][symbol]

        return None


    def __put_data( self, exchange, table, symbol , data ):
        """
            read_data 从data_q中读取数据
        Parameters:
            data_q -  数据队列，用于从connector接收数据
        Returns:
            None
        Raises:
            None
        """
        logger.info( "%s %s %s %s"%(exchange, table, symbol , data ) )
        
        if exchange not in self.datastore :
            self.datastore[exchange] = dict()

        if table not in self.datastore[exchange]:
            self.datastore[exchange][table] = dict()

        """
        if symbol not in self.datastore[exchange][table]:
            self.datastore[exchange][table][symbol] = None
        """
        if table in settings.SUBSCRIBE_TOPICS['GENERIC_SUBSCRIBE_TOPICS'] :
            self.datastore[exchange][table] = data
        else :
            self.datastore[exchange][table][symbol] = data



    def run( self ):
        # TOTO 
        # 1.检查各个链接的心跳，如果有问题，先重建链接，创建一个线程创建另外的链接
        # 2.调用DM，处理数据。。。
        # 3.调用线程。。。
        while self.live:
            if not self.q.empty():
                channel, data = self.q.get()
                #logger.info( channel )
                exchange, table, symbol = channel

                if len( data ) :
                    self.__put_data( exchange, table, symbol, data )
                    self.ready = True

            sleep(0.1)


    def exit(self):
        self.live = False
        logger.info( 'DataBoard closed...' )
       






