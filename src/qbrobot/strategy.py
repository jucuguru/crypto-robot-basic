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

from  abc import abstractmethod

## private import package

from qbrobot import tsettings
from qbrobot.util import log

#
# Helpers
#
logger = logging.getLogger()

# 
# DataBoard 负责从data_q读取数据，并维护数据面板
#
class StrategyBase():
    """
        基础的策略类，可以作为样例
        Robot 启动 Strategy 并且传递 databoard 和 connectormanager 
    """

    def __init__( self , databoard, connectormanager ):
        """
            __init__ 初始化Strategy
        Parameters:
            databoard -  , 读取最新的数据
            connectormanager - , 从中获取交易下单的链接
        Returns:
            None
        Raises:
            None
        """
        #signal only works in main thread
        atexit.register(self.exit)
        #signal.signal(signal.SIGTERM, self.exit)

        self.db = databoard
        self.cm = connectormanager

        # 定义状态
        self.live = True
        self.ready = True

    def getStatus(self):
        #logger.info( 'Strategy status:[ %s %s %s %s %s ]'%(self.live, self.ready, self.db.live, self.db.ready, self.cm.live) )
        return all((self.live, self.ready, self.db.live, self.db.ready, self.cm.live))

    def start(self):
        """
            策略线程程序的入口
        """
        t = Thread( target = self.play )
        t.daemon = True
        t.start()

    def play(self):
        """
        运行的主体逻辑 
        """
        while self.getStatus() :
            pass
            time.sleep( tsettings.INTERVAL_STRATEGY)

    def stop(self):
        """
         停止策略线程
        """
        self.live = False
        self.ready = False
        logger.info( 'Strategy closed...' )

    def exit(self):
        """
         退出策略线程
        """
        self.live = False
        self.ready = False
        logger.info( 'Strategy exited...' )


    @abstractmethod
    def pause(self):
        """
        运行的主体逻辑 
        """
        self.live = True
        self.ready = False

    @abstractmethod
    def profit(self):
        """
        运行的主体逻辑 
        """
        pass


    @abstractmethod
    def getvalue(self):
        """
        运行的主体逻辑 
        """
        pass




