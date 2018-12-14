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

    def __init__(self, data_q, exchange,  endpoint, symbol, api_key=None, api_secret=None, subtopics = None):
        '''Connect to the websocket and initialize data stores.'''
        #self.logger = logging.getLogger(__name__)
        self.logger = logger
        self.logger.debug("Initializing WebSocket.")

        self.q = data_q
        self.exchange = exchange 
        self.endpoint = endpoint
        self.symbol = symbol
        self.cid = "exchange[%s], endpoint[%s], symbol[%s]"%(exchange, endpoint, symbol)
        self.subtopics = subtopics

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
            self.logger.info('Connected to WS.')

        # Connected. Wait for partials
        if ret :
            self.__wait_for_symbol(symbol)
            if api_key:
                self.__wait_for_account()

            self.isReady = True

            self.logger.info('%s Got all market data. Starting.'%self.cid)

    def exit(self):
        '''Call this to exit - will close websocket.'''
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
        self.logger.debug("Starting thread")


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
            logger.debug("wait for timeout: %s %d"%(self.ws.sock ,   conn_timeout ) ) 
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout:
            self.logger.error("Couldn't connect to WS! Exiting.")
            self.exited = True
            self.exit()
            #raise websocket.WebSocketTimeoutException('Couldn\'t connect to WS! Exiting.')
            return False
        else :
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
        Generate a connection URL. We can define subscriptions right in the querystring.
        Most subscription topics are scoped by the symbol we're listening to.
        '''

        # You can sub to orderBookL2 for all levels, or orderBook10 for top 10 levels & save bandwidth
        symbolSubs = self.subtopics['SYMBOL_SUBSCRIBE_TOPICS']
        genericSubs = self.subtopics['GENERIC_SUBSCRIBE_TOPICS']

        subscriptions = [sub + ':' + self.symbol for sub in symbolSubs]
        subscriptions += genericSubs

        urlParts = list(urllib.parse.urlparse(self.endpoint))
        urlParts[0] = urlParts[0].replace('http', 'ws')
        urlParts[2] = "/realtime?subscribe={}".format(','.join(subscriptions))
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

    def __send_command(self, command, args=None):
        '''Send a raw command.'''
        if args is None:
            args = []
        self.ws.send(json.dumps({"op": command, "args": args}))

    def __on_message(self, ws, message):
        '''Handler for parsing WS messages.'''
        message = json.loads(message)
        self.logger.debug(json.dumps(message))

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None
        try:
            if 'subscribe' in message:
                self.logger.debug("Subscribed to %s." % message['subscribe'])
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
                channel = ( self.exchange, table, self.symbol )
                self.q.put( ( channel, self.data[table] ) )
            else:
                logger.debug( message ) 

        except:
            self.logger.error(traceback.format_exc())

    def __on_error(self, ws, error):
        '''Called on fatal websocket errors. We exit on these.'''
        if not self.exited:
            self.logger.error("%s Error : %s" % (self.cid, error) )
            #raise websocket.WebSocketException(error)
            self.isReady = False

    def __on_pong(self, ws, message ):
        logger.debug("%s ---on pong---- "% self.cid)
        self.isReady = True

    def __on_open(self, ws):
        '''Called when the WS opens.'''
        self.logger.debug("%s Websocket Opened."%self.cid)

    def __on_close(self, ws):
        '''Called on websocket close.'''
        self.logger.debug( ( '%s Websocket Closed')%(self.cid) )
        self.exited = True
        self.isReady = False


# Utility method for finding an item in the store.
# When an update comes through on the websocket, we need to figure out which item in the array it is
# in order to match that item.
#
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
