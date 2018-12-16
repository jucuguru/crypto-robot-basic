#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

import logging
import six
import time
from datetime import datetime
from threading import Thread 
from multiprocessing import Queue

## private import package
from qbrobot.util import log
from qbrobot.conn.connbase import Connector
from qbrobot.conn.btfxwss import BtfxWss

#
# Helpers
#
logger = logging.getLogger()


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

            # 开始订阅数据频道
            timeout = 5
            while not self.isReady and timeout :
                logger.debug( self.subscribed )
                self.__subscribe_chans_symbs(self.channels, self.symbol)
                if self.__check_subscribed_chan_symbol():
                    self.isReady = True
                timeout -= 1 

            #TODO 判断ticker是否订阅成功， 然后定义queue 
            self.channels_q = dict() 
            if self.isReady :
                self.channels_q = self.__set_channels_queue()

            self.isconnected = True
            self.run()
            return True
        else :
            return False


    @staticmethod
    def sort_by(array, key, descending=False):
        return sorted(array, key=lambda k: k[key] if k[key] is not None else "", reverse=descending)


    def __set_channels_queue(self):
        """
            设置订阅频道，检查订阅成功的频道，并且放入到字典容器中 
        """
        cq = dict()
        for s in self.subscribed:
            if self.subscribed[s] : 
                cs = s.split(':')
                ch = cs[0]
                sy = cs[1]
                if ch == 'ticker':
                    cq[s] = self.conn.tickers(sy)
                elif ch == 'book':
                    cq[s] = self.conn.books(sy)
                elif ch == 'trades':
                    cq[s] = self.conn.trades(sy)
                elif ch == 'candles' :
                    cq[s] = self.conn.candles(sy)
                elif ch == 'orders' : 
                    cq[s] = self.conn.orders(sy)
                elif ch == 'positions':
                    cq[s] = self.conn.positions(sy)
                elif ch == 'margin':
                    cq[s] = self.conn.margin(sy)
                elif ch == 'wallets':
                    cq[s] = self.conn.wallets(sy)
                elif ch == 'balacnce':
                    cq[s] = self.conn.balacnce(sy)
                elif ch == 'funding':
                    cq[s] = self.conn.funding(sy)
                elif ch == 'account':
                    cq[s] = self.conn.account(sy)

        return cq



    def __findChanByAltername(self, channels, altername ):
        """
            把exchange使用的channel name 转回 base 统一的channel name
        """
        base = ''

        for ch in channels:
            if altername == channels[ch]['altername']:
                base = ch
                break

        return base


    def __pass_to_robot(self, channel, data ):
        """
            转换channel， 解析data，把data从[]，转换为dict()
        """
        if not data:
            logger.info("error channel - %s , data - %s -", channel, data)
            return None

        e , c, s = channel
        b = self.__findChanByAltername(channels = self.channels, altername=c)
        chan = (e,b,s)
        ret = dict()

        if b == 'ticker':
            ret = self.__handler_ticker_data(data)
        elif b == 'book':
            ret = self.__handler_book_data(data)
        elif b == 'trade':
            ret = self.__handler_trade_data(data)
        else:
            logger.warning('channel not support, %s ', b)

        logger.debug( "%s %s"%(chan, ret ) )
        return self.q.put(( chan, ret ))


    def __handler_ticker_data(self, data):
        """
        ticker ([[3330.2, 59.51859706, 3330.3, 50.44819372, 33.9, 0.0103, 3330.2, 22646.3776218, 3371.8, 3215.2]], 1544949996.240396)
        ticker: ([[bid, bid size, ask, ask size, DAILY_CHANGE, DAILY_CHANGE_PERC, LAST_PRICE, VOLUME, HIGH, LOW]], timestamp]
        """
        ret = list()
        if not data :
            return ( ret, '' )

        ( dat, ts ) = data
        for item in dat:
            d = dict()
            try:
                d['bid_price']   = item[0] if item[0] else 0.0
                d['bid_size']    = item[1] if item[1] else 0.0
                d['ask_price']   = item[2] if item[2] else 0.0
                d['ask_size']    = item[3] if item[3] else 0.0
                d['daily_change']   = item[4] if item[4] else 0.0
                d['daily_change_perc']   = item[5] if item[5] else 0.0
                d['last_price'] = item[6] if item[6] else 0.0
                d['volume']     = item[7] if item[7] else 0.0
                d['high']       = item[8] if item[8] else 0.0
                d['low']        = item[9] if item[9] else 0.0
                d['timestamp']  = datetime.utcfromtimestamp( ts ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                ret.append(d)
            except Exception as e :
                logger.warning('%s, dat - %s , d - %s ', str(e), dat, d )

        #logger.debug("ticker - %s", ret)

        return ret


    def __handler_book_data(self, data):
        """
        book : ([[3335.1, 1, -0.4]], 1544950042.345439) 
        orderbook: ( [price, count, amount] , [price, count, amount] , timestamp )
        """
        ret = list()
        result = {
            'bids': [],
            'asks': [],
            'timestamp': None,
            'datetime': None,
            'nonce': None,
        }
        if not data :
            return ( ret, '' )

        ( dat, ts ) = data
        if isinstance(dat, list) and isinstance( dat[0], list) :
            for dd in dat:
                if isinstance( dd[0], list) :
                    for item in dd:
                        d = dict()
                        d['price']    = item[0] if item[0] else 0.0
                        d['count']    = item[1] if item[1] else 0.0
                        d['amount']   = item[2] if item[2] else 0.0
                        d['timestamp']  = datetime.utcfromtimestamp( ts ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        ret.append(d)
                else:
                    item = dd
                    d = dict()
                    d['price']    = item[0] if item[0] else 0.0
                    d['count']    = item[1] if item[1] else 0.0
                    d['amount']   = item[2] if item[2] else 0.0
                    d['timestamp']  = datetime.utcfromtimestamp( ts ).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    ret.append(d)

        if ret and len(ret):
            for o in range(0, len(ret)):
                order = ret[o]
                side = 'bids' if (order['amount'] > 0 ) else 'asks'
                amount = round(order['amount'],2)
                price  = round(order['price'],2)
                timestamp = order['timestamp']
                result[side].append([price, amount])

            result['bids'] = self.sort_by(result['bids'], 0, True)
            result['asks'] = self.sort_by(result['asks'], 0)
            result['timestamp'] = timestamp

        #logger.debug("book - %s", result)

        return result


    def __handler_trade_data(self, data):
        """
        trade: (['tu', [323466835, 1544950046473, -10.1666, 88.11]], 1544950046.690639)
               (['te', [323466742, 1544950006263, -0.01260632, 3330.2]], 1544950006.642729)
        trade: ( [flag, [SEQ/ID        TIMESTAMP.     AMOUNT    PRICE ], timestamp )
            flag == 'tu' : a “tu” message which will be delayed by 1-2 seconds and include the tradeId.
            flag == 'te' :  a “te” message which mimics the current behavior.
        """
        ret = list()
        if not data :
            return ( ret, '' )

        ( dd, ts ) = data
        if isinstance( dd[0], six.string_types ) :
            ( flag, item  ) = dd
            d = dict()
            d['seq']        = item[0] if item[0] else 0.0
            ts              = item[1] if item[1] else 0.0
            d['amount']     = item[2] if item[2] else 0.0
            d['price']      = item[3] if item[3] else 0.0
            d['flag']       = flag
            d['timestamp']  = datetime.utcfromtimestamp( float(ts)/1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            ret.append(d)
        else:
            flag = ''
            dat = dd
            for ds in dat:
                for item in ds :
                    d = dict()
                    d['seq']        = item[0] if item[0] else 0.0
                    ts              = item[1] if item[1] else 0.0
                    d['amount']     = item[2] if item[2] else 0.0
                    d['price']      = item[3] if item[3] else 0.0
                    d['flag']       = flag
                    d['timestamp']  = datetime.utcfromtimestamp( float(ts)/1000.0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    ret.append(d)

        #logger.debug("trade - %s", ret)

        return ret



    def __get_data_from_queue(self):
        """
            如果是 bitfinex 链接，定时轮询queue，并把数据传入后端
        """
        while self.exchange == 'bitfinex' and self.conntype == 'websocket'  and self.isconnected :
            channel = None
            data = None
            # 轮询channels_q
            for cq in self.channels_q:
                cs = cq.split(':')
                q = self.channels_q[cq]
                if not q.empty():
                    data = q.get(timeout=0.1)
                    channel = (self.exchange , cs[0], cs[1] )
                    self.__pass_to_robot( channel , data )

            time.sleep(0.1)


    #
    # subscribe interactive Methods added by Huangkj
    #
    def __subscribe_chans_symbs(self, channels, symbols ):
        """
            发起订阅，按照channels和symbols循环订阅，并记录下每个channel的状态是否OK
        """
        if not (channels and symbols ):
            return False

        for ch in channels :
            if channels[ch]['auth'] :
                if not self.auth:
                    continue
            chan = channels[ch]['altername']
            for sy in symbols:
                chanid = chan +':'+ sy
                if not chanid in self.subscribed  or  not self.subscribed[chanid]:
                    self.__subscribe_chan_symbol( chan, sy )
                    time.sleep(0.1)


    def __unsubscribe_chans_symbs(self, channels, symbols ):
        """
            发起订阅，按照channels和symbols循环订阅，并记录下每个channel的状态是否OK
        """
        if not (channels and symbols ):
            return False

        for ch in channels :
            if channels[ch]['auth'] :
                if not self.auth:
                    continue
            chan = channels[ch]['altername']
            for sy in symbols:
                chanid = chan +':'+ sy
                if chanid in self.subscribed and self.subscribed[chanid]:
                    self.__unsubscribe_chan_symbol( chan, sy )



    def __subscribe_chan_symbol(self, channel, symbol):
        """
            发起一次订阅，为了便于监控，一次只订阅一个channel和symbol，预先设置self.subscribed[chanid]为 Treu
        Parameters:
            channel -  数据频道，在bitmex中，对应的是subscibe，
            symbol - 品种
        Returns:
            None
        Raises:
            None
        """
        chanid = channel + ':' + symbol
        self.__register_subscribed_chan_symbol( chanid=chanid, stat=True)
        if channel == 'ticker':
            self.conn.subscribe_to_ticker(symbol)
        elif channel == 'trades':
            self.conn.subscribe_to_trades(symbol)
        elif channel == 'book':
            self.conn.subscribe_to_order_book(symbol)
        """
            如果没有登录 auth， 同时只能订阅三个channel， 所以先去掉了candles，有ticker/trade/orderbook
        elif channel == 'candles':
            self.conn.subscribe_to_candles(pair = self.symbol, timeframe = '1m')
        """

    def __unsubscribe_chan_symbol(self, channel, symbol):
        """
            发起一次订阅，为了便于监控，一次只订阅一个channel和symbol，预先设置self.subscribed[chanid]为False
        Parameters:
            channel -  数据频道，在bitmex中，对应的是subscibe，
            symbol - 品种
        Returns:
            None
        Raises:
            None
        """
        chanid = channel + ':' + symbol
        self.__register_subscribed_chan_symbol( chanid=chanid, stat=False)
        if channel == 'ticker':
            self.conn.unsubscribe_from_ticker(symbol)
        elif channel == 'trades':
            self.conn.unsubscribe_from_trades(symbol)
        elif channel == 'book':
            self.conn.unsubscribe_from_order_book(symbol)


    def __register_subscribed_chan_symbol(self, chanid = None, stat=False ):
        """
            设置self.subscribed为False
        Parameters:
            chanid -  数据频道，chanid = channel +':' + symbol
        Returns:
            None
        Raises:
            None
        """
        if chanid :
            self.subscribed[chanid]=True


    def __check_subscribed_chan_symbol(self):
        """
            检查self.subscribed的所有频道是否为True，如果有没有成功的频道继续订阅
        Parameters:
        Returns:
            ret - True / False
        Raises:
            None
        """
        if self.conn.channel_configs.values() :
            return True
        else:
            return False



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
            timeout = 5
            while self.isReady and timeout :
                self.__unsubscribe_chans_symbs(self.channels, self.symbol)
                time.sleep(0.5)
                if not self.conn.channel_configs.values() : 
                    # 有任何一个频道还没有断开，就继续尝试申请
                    self.isReady = False
                timeout -= 1

            self.conn.stop()

        self.isconnected = False
        logger.info('Websocket Connector %s was disconnected...'%(self.name))

    def getStatus(self ):
        logger.debug('websocket status check...')
        if not self.conn.conn.connected.is_set():
            logger.debug('websocket status exited')
            self.isconnected = False

        return (self.isconnected)


