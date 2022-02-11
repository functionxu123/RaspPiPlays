#  基于树莓派的物联网监控
<!-- vscode-markdown-toc -->
* 1. [实现功能](#)
* 2. [硬件准备](#-1)
* 3. [功能1--实时监控+动作视频捕捉+Flask建立网站提供服务](#1--Flask)
* 4. [功能2--内网穿透](#2--)
	* 4.1. [在公网服务器上](#-1)
	* 4.2. [在树莓派上或其他需要被映射出去的内网机器上](#-1)
	* 4.3. [在任意地方用SSH连接到内网机器](#SSH)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc -->

##  1. <a name=''></a>实现功能
 1. 通过CSI（CMOS Sensor Interface）摄像头实现： 1、实时监控 2、动作视频捕捉（当画面中有动作时自动录制视频）
 2. 利用Flask建立网站提供： 1、实时监控服务 2、动作视频查看服务
 3. 内网穿透工具，用于树莓派与主机不在同一局域网中情况下的监控

##  2. <a name='-1'></a>硬件准备
 树莓派板子（3b+）及其配套设施（参见工程根目录下README）、CSI（CMOS Sensor Interface）摄像头（预先配置好，过程参见工程根目录下README）

 ps: 如果需要实现上述功能3（内网穿透）还需要一台具有公网ip的服务器
 ***


##  3. <a name='1--Flask'></a>功能1--实时监控+动作视频捕捉+Flask建立网站提供服务
**在树莓派上**

本目录下执行：

`python FrameProc.py -tf 20 -vf 20 -d`

-t设置传输fps

-vf设置动作视频捕捉的fps

-d打开debug，会多一些命令行输出打印，功能不受影响

默认情况下在树莓派的8080端口起flask服务，同一局域网下访问服务：

1. 访问动作视频： `http://树莓派IP:8080/video`
2. 实时监控： `http://树莓派IP:8080`

 ***
##  4. <a name='2--'></a>功能2--内网穿透

*这部分要求有一个公网服务器*

###  4.1. <a name='-1'></a>在公网服务器上

**到server目录下**

1. 修改config.json文件，文件中是一个json格式的map，其中key表示获取数据端口，val表示从该key获取的数据发送到哪个端口，填写自己的端口配置，例如：
```
{
    "9002": 8002,
    "8002": 9002
}
```

2. 执行命令： `python server_port_map.py -c config.json`启动服务，等待链接

###  4.2. <a name='-1'></a>在树莓派上或其他需要被映射出去的内网机器上

**到client目录下**

1. 同样的先修改config.json文件，这里也是一个map，其中key为接受数据的server开放的IP:PORT字符串，val为要发送到server的IP:PORT字符串，这里举例映射内网中，本机的SSH(22)端口:
```
{
    "127.0.0.1:22": "ServerIP:9002",
    "ServerIP:9002": "127.0.0.1:22"
}
```
*这里注意替换ServerIP为公网服务器的IP*

2. 执行启动命令： `python local_port_map.py -d -bs`，这里-bs参数可以保证发送的稳定性，保证每个数据都稳定传输出去，否则在流量过大时可能会有丢弃

###  4.3. <a name='SSH'></a>在任意地方用SSH连接到内网机器
1. 首先要保证在内网的机器上有SSH服务，如果没有可以起一个
2. 在任意其他能联网的机器上执行： `ssh -p 8002 username@ServerIP` 即可连接到内网中的机器，其中*username*为内网机器上的登录用户名,输入的密码也是内网机器上登录密码，*ServerIP*为公网服务器IP

PS：每个端口只能连一个，多个机器用同一端口会有问题
 ***
