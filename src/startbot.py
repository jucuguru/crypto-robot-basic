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

from  qbrobot.quantrobot import QuantRobot

if __name__ == '__main__':

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






