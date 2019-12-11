## TASK-2 客户端运行环境与说明描述



#### **运行环境**

语言：Python3.7 

操作系统：Windows10

依赖库：cv2，PyAudio，pydub，simpleaudio（服务端和客户端）

PyAudio可以从https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio下载相应的.whl文件，然后pip install之。

pydub安装参考https://github.com/jiaaro/pydub#installation。



#### **如何运行**

在当前目录下命令行运行

```
python main.py
```

后面可以有如下四个参数（必须是4个）：

- 服务端RTSP端口
- 服务端用于查询影片的服务的端口
- 客户端自身的RTSP端口
- 客户端自身的用于查询影片的服务的端口

默认的端口号都是大端口，应该不需要指定这些参数。



#### **使用说明**

**测试文件**

如果要使用自己的测试文件，请将视频文件放入Server代码文件夹下的`./movies`文件夹，相应的字幕文件（必须为`.srt`文件）放入Server代码文件夹下的`./srt`文件夹并与对应视频文件的名称一致。Server会自动获取所有`./movies`文件夹里的影片资源并配上相应的字幕，此外，为了便于测试，默认每个文件的类别为其后缀（但由于库的限制，只能使用mp4或mov格式的视频，**且mov格式的声音是有问题的**（虽然可以解码））。



**注意事项**

由于同一台电脑同时运行服务端和客户端内存cpu消耗均较高，请在电源接通，内存和cpu占用较小时进行操作。此外，若要测试多客户端，请不要播放大文件，因为SETUP过程会很慢很慢。

控制台会可能会输出一些捕获到的错误，请无视，这不影响程序的运行。

此外，有的视频cv2第二次读倒数第一帧时会出错，导致在视频末尾也会显示一直在缓冲，遇到这种情况无视就好。



**进入客户端**

运行上文命令后，会跳出一个窗口：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211212834954.png" alt="image-20191211212834954" style="zoom: 50%;" />



如果不是第一次运行，那还会有一个弹出的窗口：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211212931029.png" alt="image-20191211212931029" style="zoom: 67%;" />

选择**是**则会直接加载上次的记录（加载的含义见下文）。



**控件描述**

首先，右侧自上而下依次为：类别选择框，关键词（子串）输入框，搜索结果列表和历史记录列表。其中，

- 类别选择框下拉可以选择一个类别，所有即所有类别
- 关键词（子串）输入框可以输入内容，而后点击搜索按钮可以根据类别和关键词获得最新结果并刷新结果列表
- 搜索结果列表的每一项双击都可以加载
- 历史记录列表的每一项双击也都可以加载

左下方按钮功能如其文字；三个下拉选择框分别是倍率、字幕和视频质量。



**搜索影片**

如上文控件描述中提到的，选择了类别、关键词点击搜索按钮即可搜索影片。



**加载影片**

如上所说，双击任一个列表项可以加载影片。注意，**加载**不是**播放**，加载时会出现提示：

![image-20191211214821414](C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211214821414.png)

加载完毕后也会出现提示：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211213449622.png" alt="image-20191211213449622"  />

加载过程中，其他操作均无效（除了关闭客户端和全屏），因为此时服务端正在处理`SETUP`命令，对于较大的影片需要一定时间。如果此时双击另一个影片列表项，会弹出：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211221152096.png" alt="image-20191211221152096" style="zoom: 80%;" />



**播放影片**

加载完毕后可以**点击播放**播放影片。点击暂停按钮可以暂停；拖动进度条，开始时自动暂停，释放时在新的位置播放，会有一点点缓冲时间。

播放过程中可以选择倍速、字幕（无是没有字幕，默认是使用字幕）、视频质量。由于缓冲机制，视频质量的变化需要一点时间后才会体现。

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211213823501.png" alt="image-20191211213823501" style="zoom: 67%;" />

如果需要缓冲，上图显示提示的区域会出现：

![image-20191211213914746](C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211213914746.png)

耐心等待即可。

该区域还是字幕（如有）显示的区域。如报告中所说，由于tkinter的原因，不得已出此下策，专门辟出一小条区域显示字幕以及提示信息，不过也顺带解决了字体颜色与背景色相近时的问题。字幕示例如下图：

![image-20191211214117087](C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211214117087.png)

影片播放至结尾后画面会停滞，但并非资源被回收，此时仍可以**回拉进度条重新播放**。在影片播放过程中，无论暂不暂停，都可以**双击列表中的另一个影片切换**（双击自身是无效的）。同样，双击后要先加载，需要等待加载完成。



**全屏**

为了全屏时的美观起见，全屏时除了图像和字幕以外的控件均不可见。可以通过`Esc`键退出全屏，`P`键暂停/播放。其他功能需要退出全屏调节。



**退出客户端**

要在任何时候退出客户端，点击右上角即可，会有弹出窗确认。

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211215230335.png" alt="image-20191211215230335" style="zoom:80%;" />