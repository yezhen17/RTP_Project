from PyQt5.QtWidgets import QMessageBox
import socket
import threading
from audio_player import AudioPlayer
from RtpPacket import RtpPacket
from subtitle import Subtitle

from PyQt5.QtWidgets import QMessageBox



def qt_exception_wrapper(func):
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            QMessageBox.information(self, 'Error', 'Meet with Error: ' + str(e),
                QMessageBox.Yes, QMessageBox.Yes)
    return wrapper



class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4

    # Initiation..
    def __init__(self, server_addr, server_rtsp_port, server_plp_port, rtp_port, plp_port, movie_name):

        # get addr and ports
        self.server_addr = server_addr
        self.server_rtsp_port = int(server_rtsp_port)
        self.server_plp_port = int(server_plp_port)
        self.rtp_port = int(rtp_port)
        self.plp_port = int(plp_port)

        # current movie name
        self.movie_name = movie_name

        self.rtsp_seq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0



        # current video and audio parameters
        self.packet_data = b''
        self.frameNbr = 0
        self.video_frame_no = 0
        self.video_frame_count = 0
        self.video_fps = 0
        self.audio_channels = 0
        self.audio_frame_rate = 0
        self.audio_sample_width = 0
        self.time_delay = 0
        self.modified_time_delay = 0

        # cache_settings
        self.cache_file = ''
        self.cache_extension = 'jpg'


        # self.setupMovie(movie_name)

    def retrievePlayList(self, type, keyword='', category=''):
        """
        :param keyword: keyword to search
        :param category: category to search
        :param keyword: category to search
        :return: a list of movie names
        """
        print(category)
        plp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        plp_socket.settimeout(1)
        plp_socket.bind(("", self.plp_port))
        addr = (self.server_addr, self.server_plp_port)
        if type == 'LIST':
            plp_socket.sendto('LIST'.encode('utf-8'), addr)
        elif type == 'CATEGORY':
            plp_socket.sendto('CATEGORY'.encode('utf-8'), addr)
        else:
            cmd = 'SEARCH ' + keyword + ' ' + category
            plp_socket.sendto(cmd.encode('utf-8'), addr)
        response, addr = plp_socket.recvfrom(8192)
        play_list = response.decode().split('\n')
        plp_socket.close()
        return play_list

    @qt_exception_wrapper
    def setupMovie(self, movie_name='test.mp4'):
        """Setup button handler."""
        if self.state == self.INIT or self.state == self.READY:
            self.rtsp_seq = 0
            self.movie_name = movie_name
            self.initNewMovie()
            self.connectToServer()

            self.sendRtspRequest(self.SETUP, movie_name)
        elif self.state == self.PLAYING:
            self.pauseMovie()
            self.exitClient()
            self.play_end = True
            while self.state != self.INIT:
                print("fuckkk")
            print(movie_name)
            self.movie_name = movie_name
            self.rtsp_seq = 0
            self.initNewMovie()
            self.connectToServer()

            self.sendRtspRequest(self.SETUP, movie_name)

    @qt_exception_wrapper
    def exitAttempt(self, event):
        if self.state != self.PLAYING:
            self.exitClient()
        else:
            self.pauseMovie()
            do_exit = QMessageBox.information(None, 'Quit?', 'Are you sure you want to quit?',
                                              QMessageBox.Yes | QMessageBox.No)
            if do_exit == QMessageBox.Yes:
                self.exitClient()
            else:
                self.playMovie()
                event.ignore()

    @qt_exception_wrapper
    def exitClient(self):
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window

    @qt_exception_wrapper
    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    @qt_exception_wrapper
    def playMovie(self, pos=-1):
        """Play button handler."""
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            if pos == -1:
                self.sendRtspRequest(self.PLAY)
            else:
                self.sendRtspRequest(self.PLAY, pos)

    @qt_exception_wrapper
    def listenRtp(self):
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(50000)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    self.frameNbr = rtpPacket.seqNum()
                    #print("Current Seq Num: " + str(currFrameNbr))
                    #if currFrameNbr > self.frameNbr: # Discard the late packet
                    # self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
                    if rtpPacket.payloadType() == 26:
                        if self.video_frame_no == rtpPacket.seqNum():

                            self.packet_data += rtpPacket.getPayload()
                        else:
                            self.video_frame_no = rtpPacket.seqNum()
                            self.collectFrame(self.packet_data, self.video_frame_no-1)
                            self.packet_data = rtpPacket.getPayload()
                    elif rtpPacket.payloadType() == 10:
                        self.collectAudioFrame(rtpPacket.getPayload(), self.frameNbr)
                    elif rtpPacket.payloadType() == 37:
                        self.collectSubtitle(rtpPacket.getPayload(), self.frameNbr)
                else:
                    if self.packet_data:
                        self.collectFrame(self.packet_data, self.video_frame_no)
                    break

            except Exception as e:
                print("rtpcrashed", str(e))
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    self.rtsp_seq = 0
                    self.teardownAcked = 0
                    break

    @qt_exception_wrapper
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cache_name = self.cache_file + str(self.sessionId) + self.cache_extension
        file = open(cache_name, "wb")
        file.write(data)
        file.close()
        return cache_name

    @qt_exception_wrapper
    def collectFrame(self, image):
        pass

    @qt_exception_wrapper
    def collectAudioFrame(self, sound):
        pass

    @qt_exception_wrapper
    def updateMovie(self):
        """Update the image file as video frame in the GUI."""
        # img = Image.open(imageFile)
        # photo = ImageTk.PhotoImage(img)
        # self.label.configure(image = photo, height=img.size[1])
        # self.label.image = photo
        pass

    @qt_exception_wrapper
    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.server_addr, self.server_rtsp_port))
            print(self.rtspSocket)
        except Exception as e:
            print(str(e))

    @qt_exception_wrapper
    def sendRtspRequest(self, requestCode, *args):
        """Send RTSP request to the server."""

        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtsp_seq += 1

            # Write the RTSP request to be sent.
            request = 'SETUP ' + args[0] + ' RTSP/1.0\n' + \
            'CSeq: ' + str(self.rtsp_seq) + '\n' + \
            'Transport: RTP/UDP; client_port= ' + str(self.rtp_port)
            print(request)
            # Keep track of the sent request.
            self.requestSent = self.SETUP

        elif requestCode == self.DESCRIBE and self.state == self.READY:
            # Update RTSP sequence number.
            self.rtsp_seq += 1

            # Write the RTSP request to be sent.
            request = 'DESCRIBE ' + args[0] + ' RTSP/1.0\n' + \
                      'CSeq: ' + str(self.rtsp_seq) + '\n' + \
                      'Session: ' + str(self.sessionId) + '\n' + \
                      'Accept: application/myformat'

            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            print(args)
            self.rtsp_seq += 1
            range_info = ''

            if len(args) != 0:
                range_info = '\nRange: npt = '+str(args[0])+' -'
            request = 'PLAY ' + self.movie_name + ' RTSP/1.0\n' + \
                      'CSeq: ' + str(self.rtsp_seq) + '\n' + \
                      'Session: ' + str(self.sessionId) + range_info

            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtsp_seq += 1
            request = 'PAUSE ' + self.movie_name + ' RTSP/1.0\n' + \
                      'CSeq: ' + str(self.rtsp_seq) + '\n' + \
                      'Session: ' + str(self.sessionId)

            self.requestSent = self.PAUSE

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            self.rtsp_seq += 1
            request = 'TEARDOWN ' + self.movie_name + ' RTSP/1.0\n' + \
                      'CSeq: ' + str(self.rtsp_seq) + '\n' + \
                      'Session: ' + str(self.sessionId)

            self.requestSent = self.TEARDOWN
        else:
            return
        print('\nData sent:\n' + request)
        print(self.rtspSocket)
        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())



    @qt_exception_wrapper
    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            try:
                reply = self.rtspSocket.recv(1024)

                if reply:
                    self.parseRtspReply(reply.decode("utf-8"))
                else:
                    if self.requestSent == self.TEARDOWN:
                        self.rtspSocket.shutdown(socket.SHUT_RDWR)
                        self.rtspSocket.close()
                        break
                # # Close the RTSP socket upon requesting Teardown
                # if self.requestSent == self.TEARDOWN:
                #     self.rtspSocket.shutdown(socket.SHUT_RDWR)
                #     self.rtspSocket.close()
                #     break
            except Exception as e:
                print(str(e))
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                # self.rtpSocket.shutdown(socket.SHUT_RDWR)
                # self.rtpSocket.close()
                # self.teardownAcked = 1
                break

    @qt_exception_wrapper
    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        lines = str(data).split('\n')
        seqNum = int(lines[1].split(' ')[1])
        print(lines)
        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtsp_seq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        # Update RTSP state.
                        self.state = self.READY
                        self.sendRtspRequest(self.DESCRIBE, self.movie_name)
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.DESCRIBE:
                        self.video_frame_count = int(lines[3].split('=')[-1])
                        self.video_fps = int(lines[4].split('=')[-1])
                        self.audio_channels = int(lines[5].split('=')[-1])
                        self.audio_frame_rate = int(lines[6].split('=')[-1])
                        self.audio_sample_width = int(lines[7].split('=')[-1])
                        has_subtitle = int(lines[8].split('=')[-1])
                        # if has_subtitle:
                        #     self.SubtitleBox.addItem("字幕1", '1')
                        self.time_delay = round(1 / self.video_fps, 3)
                        self.modified_time_delay = self.time_delay
                        self.audio_player = AudioPlayer(self.audio_channels, self.audio_frame_rate,
                                                        self.audio_sample_width)
                        # self.subtitle = Subtitle(self.video_frame_count, self.video_fps)
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1

    @qt_exception_wrapper
    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("", self.rtp_port))
        except Exception as e:
            print(str(e))
