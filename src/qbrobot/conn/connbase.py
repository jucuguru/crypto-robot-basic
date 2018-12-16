#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

import logging

## private import package

from qbrobot.util import log
from qbrobot.conn.subscribe import SUBSCRIPTION

#
# Helpers
#
logger = logging.getLogger()

# 
# Connector 负责管理一个链接
#
class Connector():

    def __init__(self, params, api_key, data_q ):
        self.q = data_q 
        self.name = params['name']
        self.exchange = params['exchange']
        self.type = params['type']
        self.symbol = params['symbol'].split(',')
        self.conntype = params['conntype']
        self.usage = params['usage']
        self.baseurl = params['baseurl']
        self.auth = params['auth']
        self.subscribe = params['subscribe']
        self.api_key = api_key['api_key'] if self.auth else ''
        self.api_secret = api_key['api_secret'] if self.auth else ''

        self.channels = None
        if self.usage == 'QUOTE':
            self.channels = self.__extend_channel()
            
        # 用于记录订阅频道是否成功
        self.subscribed = dict()

        self.conn = None
        self.isReady = False
        self.isconnected = False


    def __extend_channel(self):
        """
            把subscribe的信息替换为 对应的exchange和conntype类型的内容, 后续方便使用
            channels = {
                'ticker':{'altername':'ticker', 'type':'SYMBOL', 'auth':False},
                'book':{'altername':'quote', 'type':'SYMBOL', 'auth':False},
            }
        """
        channels = dict()
        if not self.subscribe or not len( self.subscribe ) :
            return channels

        for s in self.subscribe:
            if s in SUBSCRIPTION['exchange'][self.exchange] :
                channels[s] = dict()
                if s in SUBSCRIPTION['altername'][self.exchange+'.'+self.conntype] :
                    channels[s]['altername'] = SUBSCRIPTION['altername'][self.exchange+'.'+self.conntype][s] 
                else :
                    channels[s]['altername'] = ''

                if s in SUBSCRIPTION['type']['SYMBOL']:
                    channels[s]['type'] = 'SYMBOL'
                elif s in SUBSCRIPTION['type']['GENERIC']:
                    channels[s]['type'] = 'GENERIC'
                else:
                    channels[s]['type'] = ''

                if s in SUBSCRIPTION['auth'][self.exchange]:
                    channels[s]['auth'] = True
                else:
                    channels[s]['auth'] = False

        logger.debug('%s channels=[%s]'%(self.name, channels) )
        
        return channels


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

