import websocket
import threading
import traceback
from time import sleep
import json
import urllib
import math
import logging

from qbrobot.util.api_key import generate_nonce, generate_signature

from qbrobot.util import log


logger = logging.getLogger()


# Naive implementation of connecting to BitMEX websocket for streaming realtime data.
# The Marketmaker still interacts with this as if it were a REST Endpoint, but now it can get
# much more realtime data without polling the hell out of the API.
#
# The Websocket offers a bunch of data as raw properties right on the object.
# On connect, it synchronously asks for a push of all this data then returns.
# Right after, the MM can start using its data. It will be updated in realtime, so the MM can
# poll really often if it wants.
class BitMEXWebsocket:

    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200

    def __init__(self, data_q, name , exchange,  endpoint, symbol, api_key=None, api_secret=None, channels = None):
        '''Connect to the websocket and initialize data stores.'''
        #self.logger = logging.getLogger(__name__)
        self.logger = logger
        self.logger.debug("Initializing WebSocket.%s"%name)

        self.q = data_q
        self.name = name
        self.exchange = exchange 
        self.endpoint = endpoint
        self.symbol = symbol
        self.channels = channels
        # 用于记录订阅频道是否成功
        self.subscribed = dict()

        if api_key is not None and api_secret is None:
            raise ValueError('api_secret is required if api_key is provided')
        if api_key is None and api_secret is not None:
            raise ValueError('api_key is required if api_secret is provided')

        self.api_key = api_key
        self.api_secret = api_secret

        self.data = {}
        self.keys = {}
        self.exited = False
        self.isReady = False

        # We can subscribe right in the connection querystring, so let's build that.
        # Subscribe to all pertinent endpoints
        wsURL = self.__get_url()
        self.logger.info("Connecting to %s" % wsURL)
        ret = self.__connect(wsURL, symbol)

        if ret :
            # 开始订阅数据频道
            timeout = 5
            while not self.isReady and timeout :
                self.logger.debug( self.subscribed )
                self.__subscribe_chans_symbs(self.channels, self.symbol)
                sleep(1)
                if self.__check_subscribed_chan_symbol():
                    self.isReady = True
                timeout -= 1 

            self.logger.info('%s have connected to %s.'%(self.name, wsURL))

        """
        # Connected. Wait for partials 数据订阅已经成功，不用再等待了。
        if ret :
            self.__wait_for_symbol(symbol)
            if api_key:
                self.__wait_for_account()
        """
        self.isReady = True

    def exit(self):
        '''Call this to exit - will close websocket.'''
        timeout = 5
        while self.isReady and timeout :
            self.__unsubscribe_chans_symbs(self.channels, self.symbol)
            sleep(1)
            if not any( self.subscribed.values() ) : 
                # 有任何一个频道还没有断开，就继续尝试申请
                self.isReady = False
            timeout -= 1

        self.exited = True
        self.ws.close()

    def get_instrument(self):
        '''Get the raw instrument data for this symbol.'''
        # Turn the 'tickSize' into 'tickLog' for use in rounding
        instrument = self.data['instrument'][0]
        instrument['tickLog'] = int(math.fabs(math.log10(instrument['tickSize'])))
        return instrument

    def get_ticker(self):
        '''Return a ticker object. Generated from quote and trade.'''
        lastQuote = self.data['quote'][-1]
        lastTrade = self.data['trade'][-1]
        ticker = {
            "last": lastTrade['price'],
            "buy": lastQuote['bidPrice'],
            "sell": lastQuote['askPrice'],
            "mid": (float(lastQuote['bidPrice'] or 0) + float(lastQuote['askPrice'] or 0)) / 2
        }

        # The instrument has a tickSize. Use it to round values.
        instrument = self.data['instrument'][0]
        return {k: round(float(v or 0), instrument['tickLog']) for k, v in ticker.items()}

    def funds(self):
        '''Get your margin details.'''
        return self.data['margin'][0]

    def market_depth(self):
        '''Get market depth (orderbook). Returns all levels.'''
        return self.data['orderBookL2']

    def open_orders(self, clOrdIDPrefix):
        '''Get all your open orders.'''
        orders = self.data['order']
        # Filter to only open orders (leavesQty > 0) and those that we actually placed
        return [o for o in orders if str(o['clOrdID']).startswith(clOrdIDPrefix) and o['leavesQty'] > 0]

    def recent_trades(self):
        '''Get recent trades.'''
        return self.data['trade']

    #
    # End Public Methods
    #

    def __connect(self, wsURL, symbol):
        '''Connect to the websocket in a thread.'''
        # 根据bitmex官方的建议：不再支持通过 WebSocket API 的 ping 命令。
        # 如果你担心你的连接被默默地终止，我们推荐你采用以下流程：
        #   在接收到每条消息后，设置一个 5 秒钟的定时器。
        #   如果在定时器触发收到任何新消息，则重置定时器。
        #   如果定时器被触发了（意味着 5 秒内没有收到新消息），发送一个 ping 数据帧（如果支持的话），或者发送字符串 'ping'。
        #   期待一个原始的pong框架或文字字符串'pong'作为回应。 如果在5秒内未收到，请发出错误或重新连接。

        self.ws = websocket.WebSocketApp(wsURL,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         on_pong=self.__on_pong,
                                         header=self.__get_auth())

        self.wst = threading.Thread(target=lambda: self.ws.run_forever(ping_interval=20, ping_timeout=5,))
        self.wst.daemon = True
        self.wst.start()
        self.logger.debug(("Started thread websocket connect %s"%wsURL))

        # Wait for connect before continuing
        conn_timeout = 5
        while ( not self.ws.sock or not self.ws.sock.connected ) and conn_timeout:
            logger.debug("%s wait for timeout: %d"%(self.name,  conn_timeout ) ) 
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout:
            self.logger.error("%s couldn't connect to WS! Exiting."%(self.name))
            self.exited = True
            self.exit()
            #raise websocket.WebSocketTimeoutException('Couldn\'t connect to WS! Exiting.')
            return False

        return True

    def __get_auth(self):
        '''Return auth headers. Will use API Keys if present in settings.'''
        if self.api_key:
            self.logger.info("Authenticating with API Key.")
            # To auth to the WS using an API key, we generate a signature of a nonce and
            # the WS API endpoint.
            nonce = generate_nonce()
            return [
                "api-nonce: " + str(nonce),
                "api-signature: " + generate_signature(self.api_secret, 'GET', '/realtime', nonce, ''),
                "api-key:" + self.api_key
            ]
        else:
            self.logger.info("Not authenticating.")
            return []

    def __get_url(self):
        '''
        Generate a connection URL. only endpoint.
        '''
        urlParts = list(urllib.parse.urlparse(self.endpoint))
        urlParts[0] = urlParts[0].replace('http', 'ws')
        urlParts[2] = "/realtime"
        return urllib.parse.urlunparse(urlParts)

    def __wait_for_account(self):
        '''On subscribe, this data will come down. Wait for it.'''
        # Wait for the keys to show up from the ws
        while not {'margin', 'position', 'order'} <= set(self.data):
            sleep(0.1)

    def __wait_for_symbol(self, symbol):
        '''On subscribe, this data will come down. Wait for it.'''
        while not {'instrument', 'trade', 'quote'} <= set(self.data):
            sleep(0.1)


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
        self.__send_command(command='subscribe', args=[chanid])

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
        self.__send_command(command='unsubscribe', args=[chanid])


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
        if all( self.subscribed.values() ):
            logger.info("Subscribed channels %s success.", self.subscribed.keys())
            return True
        else:
            return False


    def __send_command(self, command, args=None):
        '''Send a raw command.'''
        if args is None:
            args = []
        self.ws.send(json.dumps({"op": command, "args": args}))


    def __pass_to_robot(self, channel, data ):
        """
            数据传递到后台。这里不用做channel的转换, 之前已经转回通用的base channel
        """
        logger.debug( "%s %s"%(channel, data ) )
        return self.q.put(( channel, data ))


    def __on_message(self, ws, message):
        '''Handler for parsing WS messages.'''
        message = json.loads(message)
        self.logger.debug("recv message: %s"%json.dumps(message))

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None
        try:
            if 'subscribe' in message:
                chanid = message['subscribe']
                # 分析message, 确定订阅是否成功，成功则设置 self.subscribed[channel][symbol] = True
                if 'success' in message:
                    self.logger.debug("Subscribed success to %s." % chanid )
                    self.__register_subscribed_chan_symbol( chanid=chanid, stat=True )
            elif 'unsubscribe' in message:
                chanid = message['unsubscribe']
                if 'success' in message:
                    self.logger.debug("Unsubscribe success to %s." % chanid )
                    self.__register_subscribed_chan_symbol( chanid=chanid, stat=False )

            elif action:

                if table not in self.data:
                    self.data[table] = []

                # There are four possible actions from the WS:
                # 'partial' - full table image
                # 'insert'  - new row
                # 'update'  - update row
                # 'delete'  - delete row
                if action == 'partial':
                    #self.logger.debug("%s: partial" % table)
                    self.data[table] += message['data']
                    # Keys are communicated on partials to let you know how to uniquely identify
                    # an item. We use it for updates.
                    self.keys[table] = message['keys']
                elif action == 'insert':
                    #self.logger.debug('%s: inserting %s' % (table, message['data']))
                    self.data[table] += message['data']

                    # Limit the max length of the table to avoid excessive memory usage.
                    # Don't trim orders because we'll lose valuable state if we do.
                    if table not in ['order', 'orderBookL2', 'orderBookL2_25'] and len(self.data[table]) > BitMEXWebsocket.MAX_TABLE_LEN:
                        self.data[table] = self.data[table][int(BitMEXWebsocket.MAX_TABLE_LEN / 2):]

                elif action == 'update':
                    #self.logger.debug('%s: updating %s' % (table, message['data']))
                    # Locate the item in the collection and update it.
                    for updateData in message['data']:
                        item = findItemByKeys(self.keys[table], self.data[table], updateData)
                        if not item:
                            return  # No item found to update. Could happen before push
                        item.update(updateData)
                        # Remove cancelled / filled orders
                        if table == 'order' and item['leavesQty'] <= 0:
                            self.data[table].remove(item)
                elif action == 'delete':
                    #self.logger.debug('%s: deleting %s' % (table, message['data']))
                    # Locate the item in the collection and remove it.
                    for deleteData in message['data']:
                        item = findItemByKeys(self.keys[table], self.data[table], deleteData)
                        self.data[table].remove(item)
                else:
                    raise Exception("Unknown action: %s" % action)

            # added by huangkj
            # 有数据，就开始向后传递数据
            if table :
                ch = findChanByAltername(channels = self.channels, altername=table)
                datas = self.__parse_channel_data(ch, self.data[table])
                for symbol in datas :
                    channel = ( self.exchange, ch, symbol )
                    self.__pass_to_robot( channel, datas[symbol] )

        except:
            self.logger.error(traceback.format_exc())

    def __parse_channel_data(self, channel, data ):
        """
            从bitmex接收到的数据，需要按照不同的table解析，得到symbol，然后按照symbol返回数据
            所有channel的处理格式都统一为 dict[ symbol:[data1,data2,data3] ], 所以不在按照以下channel区分处理
            if channel == 'ticker':
                ret = __handler_ticker_data(data)
            elif channel == 'book':
                ret = __handler_orderbook_data(data)
            elif channel == 'trade':
                ret = __handler_trade_data(data)
            elif channel == 'instrument':
                ret = __handler_instrumen_data(data)
        """
        ret = dict()
        if channel == 'book':
            ret = __handler_orderbook_data(data)
        else:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)
        return ret

    def __handler_instrumen_data(self, data ):
        """
        return ret = {
            'ETHUSD':[{'volume24h': 11974029, 'impactBidPrice': 85.75, 'underlying': 'ETH', 'inverseLeg': '', 'fairMethod': 'FundingRate', 'vwap': 83.01, 'turnover24h': 99393388060, 
                'optionStrikePrice': None, 'listing': '2018-07-18T12:00:00.000Z', 'prevTotalTurnover': 9831235185370, 'deleverage': True, 'markMethod': 'FairPrice', 'lastPrice': 85.85, 
                'timestamp': '2018-12-16T03:54:00.000Z', 'bankruptLimitUpPrice': None, 'fundingRate': 0.0001, 'positionCurrency': '', 'limitUpPrice': None, 'front': '2018-07-18T12:00:00.000Z', 
                'indicativeFundingRate': 0.0001, 'underlyingToSettleMultiplier': None, 'relistInterval': None, 'maxPrice': 1000000, 'rootSymbol': 'ETH', 'takerFee': 0.00075, 'fairPrice': 85.85, 
                'prevPrice24h': 83.7, 'taxed': True, 'calcInterval': None, 'reference': 'BMEX', 'publishTime': None, 'limitDownPrice': None, 'maxOrderQty': 10000000, 'riskLimit': 5000000000, 
                'totalTurnover': 9831895712035, 'referenceSymbol': '.BETH', 'sellLeg': '', 'quoteToSettleMultiplier': 30951, 'state': 'Open', 'settle': None, 'lotSize': 1, 'impactMidPrice': 85.825, 
                'openInterest': 5663679, 'prevTotalVolume': 475303713, 'askPrice': 85.85, 'expiry': None, 'multiplier': 100, 'fundingPremiumSymbol': '.ETHUSDPI8H', 'lastTickDirection': 'PlusTick', 
                'fundingTimestamp': '2018-12-16T04:00:00.000Z', 'sessionInterval': '2000-01-01T01:00:00.000Z', 'quoteCurrency': 'USD', 'optionUnderlyingPrice': None, 'fundingBaseSymbol': '.ETHBON8H', 
                'bidPrice': 85.75, 'capped': False, 'settlCurrency': 'XBt', 'highPrice': 86.5, 'publishInterval': None, 'optionStrikeRound': None, 'volume': 76619, 'openValue': 48622684215, 'hasLiquidity': True, 
                'fairBasis': 0, 'underlyingToPositionMultiplier': None, 'lowPrice': 81.05, 'limit': None, 'markPrice': 85.85, 'rebalanceTimestamp': None, 'optionMultiplier': None, 'totalVolume': 475380332, 
                'riskStep': 5000000000, 'insuranceFee': 0, 'isQuanto': True, 'foreignNotional24h': 3163930.509693124, 'isInverse': False, 'indicativeSettlePrice': 85.85, 'prevClosePrice': 82.71, 'closingTimestamp': '2018-12-16T04:00:00.000Z', 
                'settledPrice': None, 'bankruptLimitDownPrice': None, 'midPrice': 85.8, 'fundingInterval': '2000-01-01T08:00:00.000Z', 'lastPriceProtected': 85.85, 'impactAskPrice': 85.9, 'fairBasisRate': 0.1095, 
                'homeNotional24h': 38114.25537049419, 'fundingQuoteSymbol': '.USDBON8H', 'maintMargin': 0.01, 'settlementFee': 0, 'underlyingSymbol': 'ETH=', 'symbol': 'ETHUSD', 'optionStrikePcnt': None, 'initMargin': 0.02, 'typ': 'FFWCSX', 
                'makerFee': -0.00025, 'buyLeg': '', 'indicativeTaxRate': 0, 'rebalanceInterval': None, 'openingTimestamp': '2018-12-16T03:00:00.000Z', 'tickSize': 0.05, 'lastChangePcnt': 0.0257, 'turnover': 660526665}],
            'XBTUSD':[{'volume24h': 20258479, 'impactBidPrice': 3162.5553, 'underlying': 'XBT', 'inverseLeg': '', 'fairMethod': 'FundingRate', 'vwap': 3126.7588, 'turnover24h': 647913907426, 
                'optionStrikePrice': None, 'listing': '2016-05-04T12:00:00.000Z', 'prevTotalTurnover': 1475330078895908, 'deleverage': True, 'markMethod': 'FairPrice', 'lastPrice': 3165, 
                'timestamp': '2018-12-16T03:54:05.000Z', 'bankruptLimitUpPrice': None, 'fundingRate': -0.00375, 'positionCurrency': 'USD', 'limitUpPrice': None, 'front': '2016-05-04T12:00:00.000Z', 
                'indicativeFundingRate': -0.00375, 'underlyingToSettleMultiplier': -100000000, 'relistInterval': None, 'maxPrice': 1000000, 'rootSymbol': 'XBT', 'takerFee': 0.00075, 'fairPrice': 3230.72, 
                'prevPrice24h': 3120, 'taxed': True, 'calcInterval': None, 'reference': 'BMEX', 'publishTime': None, 'limitDownPrice': None, 'maxOrderQty': 10000000, 'riskLimit': 20000000000, 'totalTurnover': 1475341288249414, 
                'referenceSymbol': '.BXBT', 'sellLeg': '', 'quoteToSettleMultiplier': None, 'state': 'Open', 'settle': None, 'lotSize': 1, 'impactMidPrice': 3163.75, 'openInterest': 98770714, 'prevTotalVolume': 101498190355, 'askPrice': 3164, 'expiry': None, 
                'multiplier': -100000000, 'fundingPremiumSymbol': '.XBTUSDPI8H', 'lastTickDirection': 'PlusTick', 'fundingTimestamp': '2018-12-16T04:00:00.000Z', 'sessionInterval': '2000-01-01T01:00:00.000Z', 'quoteCurrency': 'USD', 'optionUnderlyingPrice': None, 
                'fundingBaseSymbol': '.XBTBON8H', 'bidPrice': 3163.5, 'capped': False, 'settlCurrency': 'XBt', 'highPrice': 3185, 'publishInterval': None, 'optionStrikeRound': None, 'volume': 354201, 'openValue': 3057249910442, 'hasLiquidity': True, 'fairBasis': -0.15, 
                'underlyingToPositionMultiplier': None, 'lowPrice': 3050, 'limit': None, 'markPrice': 3230.72, 'rebalanceTimestamp': None, 'optionMultiplier': None, 'totalVolume': 101498544556, 'riskStep': 10000000000, 'insuranceFee': 0, 'isQuanto': False, 
                'foreignNotional24h': 20258479, 'isInverse': True, 'indicativeSettlePrice': 3231.53, 'prevClosePrice': 3163.73, 'closingTimestamp': '2018-12-16T04:00:00.000Z', 'settledPrice': None, 'bankruptLimitDownPrice': None, 'midPrice': 3163.75, 
                'fundingInterval': '2000-01-01T08:00:00.000Z', 'lastPriceProtected': 3163.5, 'impactAskPrice': 3164.9576, 'fairBasisRate': -4.10625, 'homeNotional24h': 6479.1390742599915, 'fundingQuoteSymbol': '.USDBON8H', 'maintMargin': 0.005, 'settlementFee': 0, 
                'underlyingSymbol': 'XBT=', 'symbol': 'XBTUSD', 'optionStrikePcnt': None, 'initMargin': 0.01, 'typ': 'FFWCSX', 'makerFee': -0.00025, 'buyLeg': '', 'indicativeTaxRate': 0, 'rebalanceInterval': None, 'openingTimestamp': '2018-12-16T03:00:00.000Z', 
                'tickSize': 0.5, 'lastChangePcnt': 0.0144, 'turnover': 11209353506}],
            }
        """
        ret = dict()
        if data:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)
        return ret

    def __handler_trade_data(self, data ):
        """
        return ret = {
            'ETHUSD':[{'price': 85.85, 'homeNotional': 0.01937608990505716, 'foreignNotional': 1.663437318349157, 'grossValue': 51510, 'trdMatchID': '4125a744-bfaa-8449-eb9f-de8d556a8639', 
                'timestamp': '2018-12-16T03:52:34.227Z', 'symbol': 'ETHUSD', 'tickDirection': 'PlusTick', 'side': 'Buy', 'size': 6}],
            'XBTUSD':[{'price': 3163.5, 'homeNotional': 0.031611, 'foreignNotional': 100, 'grossValue': 3161100, 'trdMatchID': '261841bc-2efd-e80b-01b9-5accd95ba177', 
                'timestamp': '2018-12-16T03:53:38.501Z', 'symbol': 'XBTUSD', 'tickDirection': 'ZeroMinusTick', 'side': 'Sell', 'size': 100},],
            }
        """
        ret = dict()
        if data:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)
        return ret

    def __handler_orderbook_data(self, data ):
        """
        return ret = {
            'ETHUSD':[[{'symbol': 'ETHUSD', 'id': 38699998224, 'side': 'Sell', 'size': 72, 'price': 88.8}, 
                       {'symbol': 'ETHUSD', 'id': 38699998227, 'side': 'Sell', 'size': 22500, 'price': 88.65},],
            'XBTUSD':[{'symbol': 'XBTUSD', 'id': 15599682250, 'side': 'Sell', 'size': 12737, 'price': 3177.5}, 
                       {'symbol': 'XBTUSD', 'id': 15599682300, 'side': 'Sell', 'size': 4000, 'price': 3177},],
            }
        """
        ret = dict()
        result = {
            'bids': [],
            'asks': [],
            'timestamp': None,
            'datetime': None,
            'nonce': None,
        }

        if data:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)

            orderbook = ret if ret else None
            for o in range(0, len(orderbook)):
                order = orderbook[o]
                side = 'asks' if (order['side'] == 'Sell') else 'bids'
                amount = round(order['size'],2)
                price  = round(order['price'],2)
                result[side].append([price, amount])

            result['bids'] = self.sort_by(result['bids'], 0, True)
            result['asks'] = self.sort_by(result['asks'], 0)

            result['timestamp'] = time.time()

        return ret

    def __handler_orderbook_data(self, data ):
        """
        return ret = {
            'ETHUSD':[[{'symbol': 'ETHUSD', 'id': 38699998224, 'side': 'Sell', 'size': 72, 'price': 88.8}, 
                       {'symbol': 'ETHUSD', 'id': 38699998227, 'side': 'Sell', 'size': 22500, 'price': 88.65},],
            'XBTUSD':[{'symbol': 'XBTUSD', 'id': 15599682250, 'side': 'Sell', 'size': 12737, 'price': 3177.5}, 
                       {'symbol': 'XBTUSD', 'id': 15599682300, 'side': 'Sell', 'size': 4000, 'price': 3177},],
            }
        """
        ret = dict()
        if data:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)
        return ret


    def __handler_ticker_data(self, data ):
        """
        return ret = {
            'ETHUSD':[{'timestamp': '2018-12-16T03:53:50.045Z', 'symbol': 'ETHUSD', 'bidSize': 174784, 'bidPrice': 85.75, 'askPrice': 85.85, 'askSize': 41}, ], 
            'XBTUSD':[{'timestamp': '2018-12-16T03:53:53.225Z', 'symbol': 'XBTUSD', 'bidSize': 6275, 'bidPrice': 3163.5, 'askPrice': 3164, 'askSize': 7}, 
                      {'timestamp': '2018-12-16T03:54:04.596Z', 'symbol': 'XBTUSD', 'bidSize': 6275, 'bidPrice': 3163.5, 'askPrice': 3165, 'askSize': 37049}, ],
            }
        """
        ret = dict()
        if data:
            for item in data :
                symbol = item['symbol']
                if symbol in ret:
                    ret[symbol].append( item )
                else:
                    ret[symbol] = list()
                    ret[symbol].append(item)
        return ret


    def __on_error(self, ws, error):
        '''Called on fatal websocket errors. We exit on these.'''
        if not self.exited:
            self.logger.error("%s Error : %s" % (self.name, error) )
            #raise websocket.WebSocketException(error)
            self.isReady = False

    def __on_pong(self, ws, message ):
        logger.debug("%s ---on pong---- "% self.name)
        self.isReady = True

    def __on_open(self, ws):
        '''Called when the WS opens.'''
        self.logger.debug("%s Websocket Opened."%self.name)

    def __on_close(self, ws):
        '''Called on websocket close.'''
        self.exited = True
        self.isReady = False
        self.logger.debug( ( '%s Websocket Closed')%(self.name) )





# Utility method for finding an item in the store.
# When an update comes through on the websocket, we need to figure out which item in the array it is
# in order to match that item.
#

def findChanByAltername( channels, altername ):
    base = ''

    for ch in channels:
        if altername == channels[ch]['altername']:
            base = ch
            break

    return base

# Helpfully, on a data push (or on an HTTP hit to /api/v1/schema), we have a "keys" array. These are the
# fields we can use to uniquely identify an item. Sometimes there is more than one, so we iterate through all
# provided keys.
def findItemByKeys(keys, table, matchData):
    for item in table:
        matched = True
        for key in keys:
            if item[key] != matchData[key]:
                matched = False
        if matched:
            return item
