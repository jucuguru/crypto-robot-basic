# crypto-robot-basic
crypto quarter toolbox to build robot

---
#说明
 目前还只是一个简单的币圈交易框架。自动从bitmex 和 bitfinex 取数。

#安装指南
 ##操作系统
  目前只支持linux，如果是windows，需要修改目录路径。

 ##虚拟环境
  python3.2 以上， 建议使用virtualenv 虚拟环境。

 ##克隆
 从github上克隆一个环境
 git clone https://github.com/jucuguru/crypto-robot-basic.git

 ##安装所需的包
     bash bin/instpkg.sh
   or
        pip  install -r src/requirement.txt

#使用方法
  ##start
    bin/rq

  ##stop
    CTRL_C 一次不行，就两次

#其他事项
    src/settings.py 包含了所有的配置，看不懂就不用来币圈。
    
