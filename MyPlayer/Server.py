import socket
from RtpPacket import RtpPacket
import time
import threading, traceback, sys
from extract_frame import FrameExtractor, VideoCapturer
from audio_player import AudioCapturer
import ctypes
from ctypes import wintypes

winmm = ctypes.WinDLL('winmm')
winmm.timeBeginPeriod(1)

class Server:
    def __init__(self, rtsp_port, rtp_port, plp_port, src_folder):
        self.rtsp_port = int(rtsp_port)
        self.rtp_port = int(rtp_port)
        self.plp_port = int(plp_port)
        self.src_folder = src_folder
        self.rtp_socket = None
        self.plp_socket = None
        self.clients = [None] * 100  # stores the client info
        self.max_jpg_num = 182
        self.openRtp()  # open rtp port
        threading.Thread(target=self.openRtsp).start()  # start listening for rtsp connections
        threading.Thread(target=self.openPlp).start()
        self.vacancy = list(range(99, 0, -1))
        self.sessionPool = list(range(99, 0, -1))  # distributes session id
        self.play_list = ['test.mp4', 'hires.mp4']

    # open rtp port
    def openRtp(self):
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtp_socket.settimeout(0.5)

        try:
            # Bind the socket to the address using the RTP port given by the server user
            self.rtp_socket.bind(("", self.rtp_port))
        except:
            print('Unable to Bind', 'Unable to bind PORT=%d' % self.rtp_port)

    def openPlp(self):
        self.plp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Bind the socket to the address using the RTP port given by the server user
            self.plp_socket.bind(("", self.plp_port))
        except:
            print('Unable to Bind', 'Unable to bind PORT=%d' % self.plp_port)
        while True:
            try:

                query, addr = self.plp_socket.recvfrom(8192)
                print("today")
                data = query.decode()
                if data == 'LIST':

                    response = '\n'.join(self.play_list)
                    self.plp_socket.sendto(response.encode('utf-8'), addr)
                elif data.split(' ')[0] == 'SEARCH':
                    keyword = data.split(' ')[1]
                    res = []
                    for movie in self.play_list:
                        if keyword in movie.split('.')[0]:
                            res.append(movie)
                    response = '\n'.join(res)
                    self.plp_socket.sendto(response.encode('utf-8'), addr)

            except:
                break



    # open rtsp port and start listening
    def openRtsp(self):
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Bind the socket to the address using the RTP port given by the server user
            self.rtsp_socket.bind(("", self.rtsp_port))
        except:
            print('Unable to Bind', 'Unable to bind PORT=%d' % self.rtsp_port)

        # start listening for connections
        self.rtsp_socket.listen(100)
        while True:
            client, addr = self.rtsp_socket.accept()
            client_info = {'socket': client, 'addr': addr[0], 'seq': 1, 'sending': False, 'frame_num': 0}
            i = self.vacancy.pop()
            self.clients[i] = client_info
            # start listening for rstp requests
            threading.Thread(target=self.recvRtsp, args=(client, i)).start()

    # receive rtsp requests
    def recvRtsp(self, socket, i):
        while True:
            try:
                request = socket.recv(1024)
                print(request)
                if request:
                    self.parseRtspRequest(request.decode("utf-8"), i)
            except:
                break
        print("got out of rtsp thread")

    def setupVideoCapture(self, i):
        self.clients[i]['extractor'] = VideoCapturer(self.clients[i]['movie_name'], "cache.jpg")
        video_extractor = self.clients[i]['extractor']
        fps = video_extractor.fps
        frame_count = video_extractor.frame_count
        self.clients[i]['audio_extractor'] = AudioCapturer(self.clients[i]['movie_name'], fps, frame_count, '')
        pass

    def sendRtp(self, i):
        while True:
            if self.clients[i]['sending']:
                try:

                    # frame_num = self.clients[i]['frame_num']
                    #
                    # src_name = self.src_folder + '/%d.jpg' % frame_num
                    # file = open(src_name, "rb")
                    # data = file.read()
                    # file.close()
                    start_pos = self.clients[i]['start_pos']
                    # print(start_pos)
                    if start_pos is not None:
                        data, frame_no = self.clients[i]['extractor'].captureFrame(start_pos)
                        audio_data, audio_frame_no = self.clients[i]['audio_extractor'].captureFrame(start_pos)
                        print("here",start_pos)
                        self.clients[i]['start_pos'] = None
                    else:
                        data, frame_no = self.clients[i]['extractor'].captureFrame()
                        audio_data, audio_frame_no = self.clients[i]['audio_extractor'].captureFrame()
                    if frame_no != -1:
                        print(frame_no, len(data))
                        rtpPacket = RtpPacket()
                        rtpPacket.encode(2, 0, 0, 0, frame_no, 0, 26, 0, data)
                        self.sendPacket(rtpPacket, i)
                        time.sleep(0.005)  # wait for 0.01 second
                        audio_packet = RtpPacket()

                        audio_packet.encode(2, 0, 0, 0, audio_frame_no, 0, 10, 0, audio_data)

                        self.sendPacket(audio_packet, i)
                        time.sleep(0.005)  # wait for 0.01 second
                        self.clients[i]['frame_num'] = frame_no + 1
                except Exception as e:
                    print(str(e))
                    break
            elif self.clients[i]['extractor'] is None:
                break
        print("got out of rtp thread")

    # send an rtp packet
    def sendPacket(self, data, i):
        addr = self.clients[i]['addr']
        port = self.clients[i]['rtp_port']
        self.rtp_socket.sendto(data.getPacket(), (addr, port))

    # parses rtsp requests and reply them
    def parseRtspRequest(self, data, i):
        print(data)
        lines = str(data).split('\n')
        cmd = lines[0].split(' ')[0]
        rtspSeq = int(lines[1].split(' ')[1])
        if rtspSeq == self.clients[i]['seq']:
            self.clients[i]['seq'] += 1
            if cmd == 'SETUP':
                self.clients[i]['movie_name'] = lines[0].split(' ')[1]
                rtpDestPort = int(lines[2].split(' ')[-1])
                self.clients[i]['rtp_port'] = rtpDestPort
                session = self.sessionPool.pop()
                self.clients[i]['session'] = session
                reply = 'RTSP/1.0 200 OK\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                self.setupVideoCapture(i)
                threading.Thread(target=self.sendRtp, args=(i,)).start()
                print("debug")

            elif cmd == 'DESCRIBE':
                session = int(lines[2].split(' ')[-1])
                if session == self.clients[i]['session']:
                    video_frame_count = str(self.clients[i]['extractor'].frame_count)
                    video_frame_count = 'video_frame_count=' + video_frame_count + '\n'
                    video_fps = str(self.clients[i]['extractor'].fps)
                    video_fps = 'video_fps=' + video_fps # no \n
                    reply = 'RTSP/1.0 200 OK\n' + \
                            'CSeq: ' + str(rtspSeq) + '\n' + \
                            'Session: ' + str(session) + '\n'
                    reply += video_frame_count
                    reply += video_fps


            elif cmd == 'PLAY':
                print(lines)
                session = int(lines[2].split(' ')[-1])
                if len(lines) > 3:
                    range = lines[3].split('= ')[-1]
                    print(range)
                    start_pos = int(range.split('-')[0].strip())
                    print(start_pos)
                    end_pos = range.split('-')[1].strip()
                    if len(end_pos) == 0:
                        end_pos = -1
                    else:
                        end_pos = int(end_pos)
                    print(start_pos)
                else:
                    start_pos = None
                try:
                    if session == self.clients[i]['session']:
                        self.clients[i]['sending'] = True
                        self.clients[i]['start_pos'] = start_pos
                        reply = 'RTSP/1.0 200 OK\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                    else:
                        reply = 'RTSP/1.0 454 Session not found\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                except Exception as e:
                    print(str(e))

            elif cmd == 'PAUSE':
                session = int(lines[2].split(' ')[-1])
                if session == self.clients[i]['session']:
                    self.clients[i]['sending'] = False
                    reply = 'RTSP/1.0 200 OK\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                else:
                    reply = 'RTSP/1.0 454 Session not found\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)

            elif cmd == 'TEARDOWN':
                session = int(lines[2].split(' ')[-1])
                if session == self.clients[i]['session']:
                    self.clients[i]['sending'] = False
                    reply = 'RTSP/1.0 200 OK\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                else:
                    reply = 'RTSP/1.0 454 Session not found\nCSeq: ' + str(rtspSeq) + '\nSession: ' + str(session)
                self.clients[i]['socket'].send(reply.encode())
                self.clients[i]['socket'].shutdown(socket.SHUT_RDWR)
                self.clients[i]['socket'].close()
                self.clients[i]['extractor'].releaseVideo()
                self.clients[i]['extractor'] = None
                self.clients[i]['rtp_port'].shutdown(socket.SHUT_RDWR)
                self.clients[i]['rtp_port'].close()

                self.sessionPool.append(self.clients[i]['session'])
                self.vacancy.append(i)
                # self.clients = self.clients[:i] + self.clients[i+1:]
                return
            else:
                return
            print(reply)
            self.clients[i]['socket'].send(reply.encode())


if __name__ == "__main__":
    server = Server(10001, 22222, 22233, '.')