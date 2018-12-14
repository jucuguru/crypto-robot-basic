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
from os.path import getmtime

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
from  qbrobot import qsettings
from  qbrobot.connector import ConnectorManager
from  qbrobot.databoard import DataBoard
from qbrobot.strategies.arbitragestrategy import BMBFStrategy

# Used for reloading the bot - saves modified times of key files
import os
watched_files_mtimes = [(f, os.path.getmtime(f)) for f in qsettings.WATCHED_FILES]


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
        logger.info("Quant Robot start to run...")
        if self.live:
            strategy = BMBFStrategy(databoard = self.dm, connectormanager = self.cm )
            strategy.start()

        while self.live  :
            if strategy.getStatus() :
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

                self.check_file_change()

            sleep(1)


            """
            except (KeyboardInterrupt, SystemExit):
                print('Start to Shutdown all thread...')
                self.exit()
                print('All thread had Shutdown.')
                sys.exit(1)
            """

        strategy.stop()


    def exit(self):
        if self.cm :
            self.cm.exit()

        if self.dm:
            self.dm.exit()

        #sleep(6)
        self.live = False
        logger.info( 'Robot Shutdown completed...' )
    
    def restart(self):
        # TODO 重启之前是否需要保护当前场景
        logger.info("Restarting the Quant Robot...")
        self.exit()
        os.execv(sys.executable, [sys.executable] + sys.argv)


    # 
    # utility
    #    
    def check_file_change(self):
        """Restart if any files we're watching have changed."""
        for f, mtime in watched_files_mtimes:
            if getmtime(f) > mtime:
                self.restart()



if __name__ == '__main__':

    #args = parse_args()

    robot = QuantRobot(  )
    robot.run()





