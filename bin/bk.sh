#!/bin/bash

DATE_STR=`date "+%Y%m%d"`

echo $DATE_STR

BKFILE="robot_bk_$DATE_STR.tar"

cd $QR_HOME

tar cvf $BKFILE .

echo $BKFILE

zip $BKFILE.zip $BKFILE

rm -f ../backup/$BKFILE.zip
rm -f $BKFILE

mv $BKFILE.zip ../backup

echo "create backup file ../backup/$BKFILE.zip"

