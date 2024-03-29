## RTP大作业报告

#### 一、概述

本项目实现了一对基于Python语言和RTP/RTSP协议的客户端/服务器，客户端可以获取服务器所有电影的列表，并支持简单的根据关键词/分类查询；同时播放音/视频，并可以选择获取服务端发过来的字幕；配备有缓冲机制和自动同步机制，可调节进度、倍率、视频质量，尽可能确保良好用户体验。



#### 二、实现的指令

RTP实现了视频帧流/音频帧流/文本流的传输，使用数据包头的`Payload type`加以区分；由于视频帧可能超过UDP包的最大限制，采用分包处理。

RTSP实现了`SETUP`/`PLAY`/`PAUSE`/`TEARDOWN`/`DESCRIBE`/`SET_PARAMETER`。



#### 三、实现的功能

- 所有基础功能，包括基本的RTSP指令、指定播放位置、改变播放速度、多客户端等
- **音频功能**，并使用帧编号进行同步，不需要手动调整
- **字幕功能**，字幕为服务端传输的`.srt`类型文件
- **记忆功能**，包括历史记录，以及客户端重新打开后自动从上次位置播放
- **播放列表**，双击可以播放影片
- **查询功能**，支持影片的类别查询和模糊查询
- **全屏选项**，通过按钮或者`Escape`键控制
- **视频质量控制**，并非通过RTCP实现，而是用户根据缓冲情况手动控制，依托RTSP的`SET_PARAMETER`指令
- **缓冲机制**，若数据传输速度跟不上播放速度则会自动缓冲



#### 四、功能实现简述

##### **综述**

视频/音频/字幕同步统一使用帧编号（作为`sequence number`字段），而总的帧数、视频fps等必要信息通过RTSP的`DESCRIBE`指令于`SETUP`后立即获取。为了控制速度稳定且正确的播放，需要将`time.sleep()`的精度调整至最小（1毫秒），而后通过记录更换图片帧等操作的时间开销，用两帧之间时间间隔减去该开销作为真正的sleep时间，来达到播放速度基本一致且与理论值十分接近。经过测试，在电脑资源占用情况良好、电源接通的时候，两倍速播放也没有问题。

##### **网络控制**

TASK-2的逻辑基本基于TASK-1，在此描述其逻辑：

打开客户端后，先由自定义的协议获取所有影片列表和类别列表；

对于一个session，`SETUP`告知服务器初始化相关资源（如视频/音频解析器），紧接着`DESCRIBE`索要影片相关信息，如帧率、总帧数等；

之后就算加载完毕，可以通过`PLAY`,`PAUSE`指令控制播放，同时`SET_PARAMETER`控制一些设置。

切换影片或者退出客户端则通过`TEARDOWN`释放这个session，再开始一个新的或者退出。

在加载完毕期间，只要在播放，服务端RTP端口就源源不断地发送数据，直到暂停或者缓冲将满。

##### **视频播放**

使用cv2库来进行视频抽帧。cv2库虽然不能处理音频，但是提取图片帧、视频信息等绰绰有余。

通过`read()`获取帧，`get()`获取视频信息，`set()`设置位置。

##### 音频功能

音频是整个项目里最棘手的部分，然而没有音频的视频播放器效果肯定大打折扣，因此花了大力气实现音频。经过大量的调研，我选用了**pydub**和**PyAudio**这两个Python库。pydub可以方便地将音频切分成帧，并可以调节速度，而PyAudio则拥有高效的流播放功能（相比于pydub）。两者结合使用达到了较好的音频播放效果。

为了达到音视频同步，音频的解析需要先获取视频的帧率，并通过帧编号来标志音频的播放位置。播放时，在一个循环内更换图片帧，同时另开一个线程播放音频帧。

##### **重新设置播放位置**

此功能的实现在GUI上依赖于进度条，指令上依赖于`PLAY`的可选参数。进度条拖动开始时自动暂停，结束时继续播放并指定由进度条位置确定的播放开始位置帧编号。服务器端收到指令后便会更改视频、音频、字幕解码器的当前位置，从新的位置发送RTP包。

##### **播放倍率设置**

对于视频而言，播放倍率的控制通过缩小或增大两相邻帧之间的间隔来实现；对于音频而言，使用pydub库以待播放音频的字节数据生成一段高于/低于原采样率的音频，再将变化后的音频以原采样率播放即可。

##### **字幕功能**

本项目支持使用服务端提供的`.srt`格式字幕文件。字幕文件的解析在服务端进行，附带上起始和结束位置的帧编号，然后在相应的时间发送至客户端，解析和传输的时间均非常短。客户端同样根据帧编号来在正确的时间播放字幕。

tkinter有一个致命的问题：不支持透明控件。我尝试了几种方法，包括：

1. 客户端使用PIL.Image库在图片上压入字幕。效果虽好，但二倍速下播放效果受到了不可忽略的影响（处理时间超过了两帧之间的间隔）；可想而知在服务端应用的话影响只增不减
2. 使用`Canvas`控件作为“画布”显示图片帧，在`Canvas`上绘制字幕文字。然而绘制效率降低也降低到不可接受的地步
3. 人为在底端增加一段很窄的黑色背景`Label`。虽然会遮挡图像的最底端，但遮挡的部分通常无关紧要，同时也解决了字幕颜色与背景颜色相同时的看不清的问题（甚至可以在这片区域显示一些其他的提示）。

经过权衡，选择了第三种方案。

##### **记忆功能**

历史记录的列表很简单，不再赘述；重新登上客户端时会询问是否从上次断开的位置播放，如果选择是则获取上次观看影片的资源，再设定开始的帧编号，点击播放则可以直接从该位置播放。

##### **播放列表与查询功能**

对照协议文档，发现该功能不属于RTP/RTCP/RTSP的任何一个。经过资料查询，有通过http协议的类似功能的实现。由于http协议较为复杂，该功能的实现采用了自定义的一套指令和格式，包括`LIST`,`CATEGORY`和`SEARCH`。其中`LIST`用于询问服务器的所有影片列表，`CATEGORY`用于询问服务器的所有影片类别列表（如科幻/动作/爱情），`SEARCH`用于根据给定条件查询满足条件的影片列表。前两者不需要参数，`SEARCH`支持类别参数和关键词参数，这里关键词比较简单，就是影片名的子串。

##### **全屏选项**

全屏选项是通过将窗口全屏化再放大播放图片用到的`Label`控件。

##### 缓冲机制

缓冲机制的实现依赖了一种自定义的类似循环链表和队列的结构，命名为`FrameQueue`。具体来说，一部影片的播放包含以下阶段：

1. 缓冲用尽（包括最开始时缓冲为空），画面暂时不变化（不是暂停！），同时提示正在缓冲
2. 缓冲积累
3. 缓冲的存量达到一个阈值，结束缓冲，开始流畅播放
4. 若传输速度较快，缓冲的存量会越来越多，因此设置了上限，到达上限后，向服务器发送RTSP的`SET_PARAMETER`指令，告诉服务器减缓发送速度（但客户端继续播放）
5. 当缓冲存量消耗到一定程度，发送RTSP的`SET_PARAMETER`指令，告诉服务器恢复正常发送速度
6. 若传输速度较慢，缓冲的存量会越来越少，直到状态1

使用Python列表模拟缓冲队列，以两个数标志队首和队尾。收到服务器的RTP包时，在队尾位置存入该数据，队尾前进一位；一帧过去，消耗了图片/音频帧后，丢弃队首位置的数据，队首前进一位。

使用如上缓冲机制，保证了只要播放，就是流畅的，大大提升了用户体验。甚至在网速良好的时候，缓冲的自动防溢出机制还会限制服务器传输速度，节省带宽。



#### 四、效果展示

由于在Client的使用说明中已经写了操作指南，这里仅作效果展示。

搜索结果：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211225756358.png" alt="image-20191211225756358" style="zoom: 67%;" />

播放中：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211225538563.png" alt="image-20191211225538563" style="zoom: 25%;" />

缓冲中：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211225942406.png" alt="image-20191211225942406" style="zoom: 25%;" />

全屏：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211230013506.png" alt="image-20191211230013506" style="zoom: 25%;" />

字幕（虽然与不是这个视频的）：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211230120790.png" alt="image-20191211230120790" style="zoom: 33%;" />

多客户端：

<img src="C:\Users\13731\AppData\Roaming\Typora\typora-user-images\image-20191211231931851.png" alt="image-20191211231931851" style="zoom:25%;" />



#### 五、**调试过程**

使用PyCharm开发。由于网络比较难调试，我在很多可能报错的地方都加了`try except`逻辑打印错误信息。此外，使用如下代码片段可以捕获到一些本来直接导致崩溃的错误。

```python
sys._excepthook = sys.excepthook
def exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)
sys.excepthook = exception_hook
```



#### 六、遇到的问题和解决方法

1. 音视频抽帧与播放。我花了长时间调研才确定了使用的Python库，得到了现在的还算比较流畅的解决方案。
2. 网络与线程管理。我用tkinter重写了GUI，因为之前用pyqt5线程处理的不是很好，经常崩溃（pyqt必须要使用qthread）在重写的时候我重构了一些内容，照顾了每个线程的安全性，尤其是注重了套接字错误的捕获等，解决了问题。
3. 同步和缓冲机制。同步和缓冲机制放在一起比较复杂，需要有大量的条件判断，我在经过了不少调试才最终达到了现在比较好的效果。
4. 字幕的处理。如上文所说，我尝试了很多方法，最终选取了性能最好的方法。



#### 七、部分参考资料

cv2：https://blog.csdn.net/qhd1994/article/details/80238707

音频抽帧+播放：https://www.programcreek.com/python/example/89506/pydub.AudioSegment.from_file

音频变速：https://stackoverflow.com/questions/51434897/how-to-change-audio-playback-speed-using-pydub

tkinter：https://www.tutorialspoint.com/python/python_gui_programming.htm

