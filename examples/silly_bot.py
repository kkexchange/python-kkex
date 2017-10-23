import time
from random import random, choice
import argparse
from decimal import Decimal
from kkex.exchange import Client

def main():
    parser = argparse.ArgumentParser(
        prog='silly kkex trader')

    parser.add_argument(
        'key',
        type=str,
        help='api key')

    parser.add_argument(
        'secret',
        type=str,
        help='api secret')

    parser.add_argument(
        '--symbol',
        type=str,
        default='BCHBTC',
        help='trade symbol')

    parser.add_argument(
        '--bpsell',
        type=float,
        default=0.0,
        help='base sell price')

    parser.add_argument(
        '--bpbuy',
        type=float,
        default=0.0,
        help='base buy price')

    parser.add_argument(
        '--var',
        type=float,
        default=0.1,
        help='privar variation')

    parser.add_argument(
        '--bm',
        type=float,
        default=1.0,
        help='base amount')

    parser.add_argument(
        '--server',
        type=str,
        default='https://kkex.com',
        help='api server')

    args = parser.parse_args()
    bot = Bot(args)
    bot.run()

class Bot:
    def __init__(self, args):
        self.args = args
        self.client = Client(
            args.key, args.secret,
            api_root=args.server)
        self.product = None
        self.base_sell_price = Decimal(args.bpsell)
        self.base_buy_price = Decimal(args.bpbuy)
        self.price_var = args.var
        assert self.price_var < 1
        self.base_amount = Decimal(args.bm)

    def fetch_products(self):
        r = self.client.get_products()
        print('products', r)
        for p in r['products']:
            if p['symbol'] == self.args.symbol:
                self.product = p
                return

    def run(self):
        self.fetch_products()
        while True:
            self.get_info()
            self.run_once()
            time.sleep(6.0 * random())

    @property
    def ask_asset(self):
        assert self.product is not None
        return self.product['mark_asset']

    @property
    def bid_asset(self):
        assert self.product is not None
        return self.product['base_asset']

    @property
    def symbol(self):
        assert self.product is not None
        return self.product['symbol']

    @property
    def avail_bid(self):
        return Decimal(
            self.userinfo['info']['funds']['free'][self.bid_asset])

    @property
    def frozen_bid(self):
        return Decimal(
            self.userinfo['info']['funds']['freezed'][self.bid_asset])

    @property
    def avail_ask(self):
        return Decimal(
            self.userinfo['info']['funds']['free'][self.ask_asset])

    @property
    def frozen_ask(self):
        return Decimal(
            self.userinfo['info']['funds']['freezed'][self.ask_asset])

    @property
    def last_price(self):
        return Decimal(
            self.userinfo['ticker']['last'])

    def get_info(self):
        self.userinfo = self.client.get_userinfo()
        print(self.userinfo)
        self.ticker = self.client.ticker(self.symbol)
        self.depth = self.client.depth(self.symbol, merge=0.01)

    def random_var(self):
        return Decimal(random() * self.price_var)

    def random_var_factor(self):
        var_base = Decimal(1-self.price_var * 0.5)
        return var_base + self.random_var()

    def clean_orders(self):
        #trade_history = self.client.get_trade_history(self.symbol)
        max_len_orders = 40
        pending_orders = self.client.get_orders(
            self.symbol, pagesize=200)['orders']
        print('orders', len(pending_orders))
        if len(pending_orders) > max_len_orders:
            rem_len = min(max(len(pending_orders) - max_len_orders + 5, 0), 20)
            for order in pending_orders[::-1][:rem_len]:
                if order['type'] in ('buy', 'sell'):
                    oid = order['order_id']
                    print('cancel order ', oid, 'of', len(pending_orders))
                    print(self.client.cancel_order(self.symbol, oid))

    def run_once(self):
        self.clean_orders()

        actions = []
        if self.base_sell_price >= -0.01:
            actions.append(self.buy)

        if self.base_buy_price >= -0.01:
            actions.append(self.sell)

        if actions:
            fn = choice(actions)
            fn()

    def trade_amount(self):
        if self.base_amount > 0.01:
            max_amount = self.base_amount * (Decimal('0.95') + Decimal(random()*0.1))
        else:
            max_amount = Decimal('0.95') + Decimal(random()*0.1)
        return max_amount

    def sell(self):
        if self.base_sell_price > 0.01:
            sell_price = self.base_sell_price * self.random_var_factor()
        else:
            sell_price = Decimal('1.0') * self.random_var_factor()

        if random() < 0.6:
            self.sell_limit(sell_price)
        else:
            self.sell_market()


    def buy(self):
        if self.base_buy_price > 0.01:
            buy_price = self.base_buy_price * self.random_var_factor()
        else:
            buy_price = Decimal('1.0') * self.random_var_factor()

        if random() < 0.6:
            self.buy_limit(buy_price)
        else:
            self.buy_market()


    def buy_limit(self, price):
        # buy
        amount = min(self.trade_amount(), self.avail_bid / price)
        if amount > 0.1:
            print('buy amount', amount, price)
            r = self.client.buy_limit(self.symbol,
                                      amount, price)

            self.print_order(r)

    def sell_limit(self, price):
        amount = min(self.trade_amount(), self.avail_ask)
        if amount > 0.1:
            print('sell amount', amount, price)
            r = self.client.sell_limit(self.symbol,
                                       amount, price)
            self.print_order(r)

    def buy_market(self):
        tamount = Decimal(self.trade_amount())
        if self.base_buy_price > 0.01:
            max_buy_amount = tamount * self.base_buy_price
        else:
            max_buy_amount = tamount

        amount = min(max_buy_amount, self.avail_bid)
        if amount > 0.1:
            print('buy market', amount)
            r = self.client.buy_market(self.symbol, amount)
            self.print_order(r)

    def sell_market(self):
        amount = min(self.trade_amount(), self.avail_ask)
        if amount > 0.1:
            print('sell market', amount)
            r = self.client.sell_market(
                self.symbol, amount)
            self.print_order(r)

    def print_order(self, r):
        if 'order_id' in r:
            return self.client.order_info(
                self.symbol,
                r['order_id'])
        else:
            print(r)

if __name__ == '__main__':
    main()
