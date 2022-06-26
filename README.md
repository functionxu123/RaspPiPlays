<!-- vscode-markdown-toc -->
* 1. [系统](#)
	* 1.1. [**装系统**](#-1)
	* 1.2. [**一些初始修改**](#-1)
		* 1.2.1. [**启动ssh服务**](#ssh)
		* 1.2.2. [**配置wireless网络**](#wireless)
	* 1.3. [**小结**](#-1)
* 2. [摄像头](#-1)
	* 2.1. [**安装raspi-config软件**](#raspi-config)
	* 2.2. [**使能摄像头**](#-1)
	* 2.3. [**小结**](#-1)
* 3. [PS](#PS)

<!-- vscode-markdown-toc-config
	numbering=true
	autoSave=true
	/vscode-markdown-toc-config -->
<!-- /vscode-markdown-toc --> [toc]
 
# RaspPiPlays
基于树梅派3b+做的一些小项目


 ***
##  1. <a name=''></a>系统
硬件准备：树莓派板子（3b+）、micro SD卡（>=16g）、读卡器（读写SD卡用）、一台PC

###  1.1. <a name='-1'></a>**装系统**
流程：在主机上将树莓派系统烧到SD卡上，SD卡安在板子上即可上电启动

推荐用官方提供的Raspberry Pi Imager工具烧系统到SD卡上：https://www.raspberrypi.com/software/ 

装好该软件后连上SD卡，选择系统和移动设备，会自动下载系统烧录，等一段时间

这里选用的是ubuntu20.04 LTS server版本（server版本为纯命令行，如果需要桌面可以选desktop版本）

###  1.2. <a name='-1'></a>**一些初始修改**
在把SD卡装到板子上之前，可以做一些文件修改以使系统具备一些初始功能，便于我们后续实现远程脱离屏幕操作



####  1.2.1. <a name='ssh'></a>**启动ssh服务**
启动该服务后就可以通过命令行远程连接进行后续配置，如果没有该服务，我们可能还需要连上屏幕、键盘才能操作

在PC上打开SD卡，在： writable/boot 下面新建一个名字为ssh的文件即可

官方说明： https://www.raspberrypi.com/documentation/computers/configuration.html#ssh-or-ssh-txt

####  1.2.2. <a name='wireless'></a>**配置wireless网络**
 *不保证成功，最好还是先用有线，不过想用无线网的可以试试*

同样是在 writable/boot 下面新建一个 wpa_supplicant.conf 文件，内容如下：
```
country=CN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
        scan_ssid=1
        ssid="wifiname"
        psk="password"
        proto=RSN
        key_mgmt=WPA-PSK
        pairwise=CCMP
        auth_alg=OPEN
}
```

官方说明：https://www.raspberrypi.com/documentation/computers/configuration.html#configuring-networking-2

最后需要注意：

1. 如果不行，试试直接把这个文件直接放到： `/etc/wpa_supplicant/wpa_supplicant.conf`
2. 也有人说应该给wpa_supplicant.conf文件加上权限： `sudo chmod a+x wpa_supplicant.conf`
3. 如果不行，可能是wifi没打开，那就只能先用有线连上了
4. 如果是修改了wifi密码后重新链接，注意修改`/etc/network/interfaces`文件

###  1.3. <a name='-1'></a>**小结**
到这里如果ssh服务正常，且树莓派能正常连接网络，我们就可以查看路由器中连接设备的ip了，找到树莓派ip，在PC上用SSH连上操作了 *否则就只能自己找个屏幕、键盘什么的连上看看问题了。。。。*
 ***

##  2. <a name='-1'></a>摄像头
这里额外买了个CSI（CMOS Sensor Interface）摄像头，安装好硬件后，记录下配置过程 **以下操作都在树莓派上进行**

*如果用官方Raspiberry PI系统应该会简单很多，这里用的Ubuntu 会有一些坑*

###  2.1. <a name='raspi-config'></a>**安装raspi-config软件**
Ubuntu系统是不自带这个的（带了就跳过这一步），需要自行安装：
1. 去官网找deb包安装： `http://mirrors.ustc.edu.cn/archive.raspberrypi.org/debian/pool/main/r/raspi-config/` 这里注意不要选太新的包，目前来看最新的是针对Pi4的硬件的，在Pi3上不好用，我用的： `wget http://archive.raspberrypi.org/debian/pool/main/r/raspi-config/raspi-config_20201027_all.deb`
2. 把包安上：
    1. 先安装包： `sudo dpkg -i raspi-config_20201027_all.deb` 发现会有依赖问题
    2. 然后`sudo apt install -f` 填补上依赖
    3. 最后再重新 `sudo dpkg -i raspi-config_20201027_all.deb` *如果过程中遇到下载什么的问题，换源试试*

###  2.2. <a name='-1'></a>**使能摄像头**
1. 命令： `sudo raspi-config` 打开配置程序
2. 路径： `Interface Option -> Camera ` Enable摄像头， 遇到问题`firmware out of date...no start_x.elf`什么的， 执行`mount /dev/mmcblk0p1 /boot` 将boot分区所在的设备号挂载到/boot上，参考： `https://blog.csdn.net/qq_34493401/article/details/107672691`

###  2.3. <a name='-1'></a>**小结**
到这里如果摄像头启动正常，执行 `ls /dev/video*` 就能看到video0这个设备了（或者执行 `vcgencmd get_camera` 能看到 `supported=1 detected=1` 也一样）

如果还不行：
1. 试试加入驱动模块进去： `sudo vim /etc/modules` 加入一行 `bcm2835-v4l2`
```
# /etc/modules: kernel modules to load at boot time.
#
# This file contains the names of kernel modules that should be loaded
# at boot time, one per line. Lines beginning with "#" are ignored.
bcm2835-v4l2
```
2. 上面说的修改配置后都要求重启才能生效
3. 如果还不行可能是硬件连接问题或者静电损坏了摄像头（很容易出现这个问题，安装时候要注意防静电）


##  3. <a name='PS'></a>PS
1. `raspi-config` 中也可以设置wifi
