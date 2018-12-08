#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

# import bulit in package
import argparse
import atexit
import signal
import sys
import traceback
import ssl
from datetime import datetime
import time
from time import sleep
import json
from decimal import Decimal
import logging
import threading
from threading import Thread, Event, Timer
from multiprocessing import Queue
from collections import OrderedDict

"""
from future.utils import iteritems
from future.standard_library import hooks
with hooks():  # Python 2/3 compat
    from urllib.parse import urlparse, urlunparse
"""

#
# Helpers
#
from  qbrobot.util import log
logger = log.setup_custom_logger()

## private import package
from  qbrobot import settings
from  qbrobot.connector import ConnectorManager
from  qbrobot.databoard import DataBoard


# Used for reloading the bot - saves modified times of key files
import os
watched_files_mtimes = [(f, os.path.getmtime(f)) for f in settings.WATCHED_FILES]


class QuantRobot( Thread ):

    # 初始化对象
    def __init__( self , ):

        # 0. had load setting , 
        # 1. 创建日志，要求每个模块都要引用 logger = log.setup_custom_logger(__name__), 在模块自身内引用logger
        # 2. 创建关键类型
        # 2.1 创建Queue用于与前方的API connector通讯
        Thread.__init__(self)

        atexit.register(self.exit)
        signal.signal(signal.SIGTERM, self.exit)

        logger.info( 'Initialize Quant Robot...' )
        data_q = Queue()
        self.q = data_q 
        self.cm = None
        self.dm = None

        # 2.2 创建链接管理器线程，添加链接
        self.cm = ConnectorManager( self.q )
        if self.cm.live :
            self.cm.start( )
        else:
            logger.error( 'Initialize failed...' )
            self.exit()
            sys.exit(0)

        # 2.3 创建数据公告板
        self.dm = DataBoard(self.q)
        self.dm.start()

        # TODO 判断错误，退出机器人

        self.live = True
        logger.info( 'Initialize completed...' )


    def run(self ):
        # TOTO 
        # 1.检查各个链接的心跳，如果有问题，先重建链接，创建一个线程创建另外的链接
        # 2.调用DM，处理数据。。。
        # 3.调用策略线程。。。
        while self.live  :
            if self.dm.live and self.dm.ready:
                strategy( self.dm )
                """
                inst_xbt = self.dm.get_data( 'bitmex', 'instrument', 'XBTUSD' )
                inst_eth = self.dm.get_data( 'bitmex', 'instrument', 'ETHUSD' )

                if inst_xbt and inst_eth :
                    xbt = inst_xbt[0]
                    eth = inst_eth[0]
                    print( u'WS----XBTUSD 当前时间:[%s], 费率时间:[%s], 最新费率:[%s] , 预测费率:[%s] '%( 
                            datetime.utcnow(), xbt['fundingTimestamp'],  xbt['fundingRate'], xbt['indicativeFundingRate'] ) )
                    print( u'WS----ETHUSD 当前时间:[%s], 费率时间:[%s], 最新费率:[%s] , 预测费率:[%s] '%( 
                            datetime.utcnow(), eth['fundingTimestamp'],  eth['fundingRate'], eth['indicativeFundingRate'] ) )
                else:
                    print( u'no data')


                margin = self.dm.get_data(exchange = 'bitmex', table = 'margin',)
                wallet = self.dm.get_data(exchange = 'bitmex', table = 'wallet',)
                order  = self.dm.get_data(exchange = 'bitmex', table = 'order', symbol = 'XBTUSD')
                execution  = self.dm.get_data(exchange = 'bitmex', table = 'execution', symbol = 'XBTUSD')
                print("margin: %s"% margin )
                print("wallet: %s"% wallet )
                print("order: %s"% order )
                print("execution: %s"% execution )
                print('\n')
                """

            sleep(2)


            """
            except (KeyboardInterrupt, SystemExit):
                print('Start to Shutdown all thread...')
                self.exit()
                print('All thread had Shutdown.')
                sys.exit(1)
            """


    def exit(self):
        self.live = False
        if self.cm :
            self.cm.exit()

        if self.dm:
            self.dm.exit()

        logger.info( 'Robot Shutdown completed...' )
        

def strategy( db = None ):
    exchange = ['bitmex', 'bitfinex' ] 
    table = [
        # for bitmex
        'quote', 'orderBookL2_25', 'instrument', 'trade', 
        # for bitfinex
        'ticker', 'order', 'book', 'candle', 'account'
        ]
    symbol = ['ETHUSD', 'XBTUSD', 'BTCUSD']

    if not ( db and db.live and db.ready ) :
        return 

    for e in exchange:
        for t in table:
            for s in symbol:
                data = db.get_data(e, t, s )
                if data :
                    logger.info( 'recv data:', data )
                else:
                    logger.info( 'recv. no data ' )




if __name__ == '__main__':

    #args = parse_args()

    robot = QuantRobot(  )
    robot.run()





