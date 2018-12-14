#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
# ##################################################################
#  Quant Robot for Cryptocurrency
# author: Huang kejie
# Date : 2018.11.26
##################################################################

# import bulit in package
#import argparse
import sys
import argparse

from  qbrobot.quantrobot import QuantRobot


def parse_args():
    """
        # TODO , start for robot / quoter / monitor
    """

    parser = argparse.ArgumentParser(description='Quant Robot Server')

    parser.add_argument('--timeframe', '-t', default = 'M',
                        help='datas timeframe: Y-year, W-week, D-day, H-hour, M-minute, T-tick')

    parser.add_argument('--data0', 
                        default='data/AgTD_1D_20061030_20180427.csv',
                        help='1st data into the system')

    parser.add_argument('--data1',
                        default='data/AgLD_1D_20150204_20180427.csv',
                        help='2nd data into the system')

    parser.add_argument('--fromdate', '-f',
                        default='2015-02-04',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--enddate', '-e',
                        default='2018-04-27',
                        help='Starting date in YYYY-MM-DD format')

    parser.add_argument('--runnext', action='store_true',
                        help='Use next by next instead of runonce')

    parser.add_argument('--nopreload', action='store_true',
                        help='Do not preload the data')

    parser.add_argument('--oldsync', action='store_true',
                        help='Use old data synchronization method')

    parser.add_argument('--printout', default=False, action='store_true',
                        help='Print out the price stdmean and Transactions. ')

    parser.add_argument('--plot', '-p', default=False, action='store_true',
                        help='Plot the read data')

    parser.add_argument('--numfigs', '-n', default=1,
                        help='Plot using numfigs figures')

    parser.add_argument('--signalfile', default='',
                        help='output the datas ,spread , signals to file.')

    parser.add_argument('--tradefile', default='',
                        help='output the tradeinfo to file')

    parser.add_argument('--orderfile', default='',
                        help='output the orderinfo to file')

    parser.add_argument('--analysfile', default='',
                        help='output the analysis report to file')

    #------------------broker and trade parameters----------------------# 
    parser.add_argument('--cash', default=100000, type=int,
                        help='Starting Cash')

    parser.add_argument('--fixed_tradecash', default=False, action='store_true',
                        help='固定交易资金量为初始资金，不随盈利和亏损波动. ')

    parser.add_argument('--comm', default=2.5, type=float,
                        help='fixed commission (2.5')

    parser.add_argument('--stake', default=10, type=int,
                        help='Stake to apply in each operation')

    parser.add_argument('--coc', default=False, action='store_true',
                        help='cheat on close, use close[0] to trading.')

    parser.add_argument('--ewmmode', action='store_true', default=False,
                        help='打开 EWM模式，使用指数移动平均线(expma)方法计算均值和标准差. ')

    parser.add_argument('--afamode', action='store_true', default=False,
                        help='打开 AFA模式，使用自适应平均线(auto fit average)方法计算均值和标准差. ')

    parser.add_argument('--riskfreerate', default=0.04, type=float,
                        help='risk free rate (0.04 or 4%')

    #------------------strategy parameters----------------------# 

    parser.add_argument('--fixedzscore', action='store_true', default=False,
                        help='Fixed the mean and stddev in bought datetime. ')

    parser.add_argument('--period', default=30, type=int,
                        help='Period to apply to the Simple Moving Average')

    parser.add_argument('--cuscore_limit', default=5600, type=int,
                        help='cuscore的阈值，用于判断cuscore是否已经偏离趋势')

    parser.add_argument('--cuscore_close', action='store_true', default=False,
                        help='关闭cuscore的阈值止损，不再判断cuscore是否已经偏离趋势，不再CUSCORE止损')

    parser.add_argument('--adj_period', default=30, type=int,
                        help='Period to adjust the mean and stddev')

    parser.add_argument('--fixedslope', default=0.0, type=float,
                        help='if fixedslope equal 0 then PAIR FACTOR will use the OLS.slope. ')

    parser.add_argument('--intercept', default=0.0, type=float,
                        help='intercept will effective if fixedslope not equal 0 ')

    parser.add_argument('--stop_limit', default=2500,  type=float,
                        help='upper stop limit. default is none.')

    parser.add_argument('--signal_limit', '-u', default=2,  type=float,
                        help='upper limit. default is 2 * spread_mean.')

    parser.add_argument('--medium_limit', default=0.1,  type=float,
                        help='upper medium. default is 0.1 * spread_mean.')

    parser.add_argument('--time_stop', default=30, type=int,
                        help='time to stop. default is 30 days.')

    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    robot = QuantRobot(  )
    robot.setDaemon(True)

    try :
        robot.start()
        robot.join()

        print('MainThread runner normal shutdown.')
        sys.exit(0)

    except (KeyboardInterrupt, SystemExit):
        print('MainThread runner shutdown.')
        robot.exit()
        robot.join(timeout=2)
        sys.exit(1)






