import cv2


class VideoCapturer:
    def __init__(self, video):
        self.video = cv2.VideoCapture(video)
        self.capturing = True
        self.frame_weight = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))  # 3 is cv2.CAP_PROP_FRAME_WIDTH
        self.frame_height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 4 is cv2.CAP_PROP_FRAME_HEIGHT
        self.frame_count = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))  # 7 is cv2.CAP_PROP_FRAME_COUNT
        self.fps = int(self.video.get(cv2.CAP_PROP_FPS))  # 5 is cv2.CAP_PROP_FPS
        self.frame_no = 0  # frame number starts from 0
        self.resize_rate = 1

    def captureFrame(self, pos=-1):
        """
        captures video frame
        :param pos: start position, if -1 then use current position
        :return: bytes of the captured frame
        """
        print(self.frame_count, self.frame_no)
        if pos != -1:
            if pos >= self.frame_count:
                return '', -1
            self.frame_no = pos
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.frame_no)
        if self.frame_no >= self.frame_count:
            return '', -1

        success, image = self.video.read()
        if success:
            if self.resize_rate != 1:
                height, width = image.shape[:2]
                new_size = (int(width * self.resize_rate), int(height * self.resize_rate))
                image = cv2.resize(image, new_size)
            self.frame_no += 1
            data = cv2.imencode('.jpg', image)[1].tobytes()
            return data, self.frame_no - 1
        else:
            print("Read", self.frame_no, "failed!")
            return '', -1

    def releaseVideo(self):
        """
        release the video
        """
        self.video.release()
        print("Video released")


class SubtitleExtractor:
    def __init__(self, subtitle_file):
        self.support_subtitle_ext = ['srt']
        assert subtitle_file.split('.')[-1] in self.support_subtitle_ext
        f = open(subtitle_file)
        self.subtitle = f.read().split('\n')
        f.close()
        self.line_no = 0
        self.subtitle_no = 0

    def extractLine(self):
        try:
            while self.subtitle[self.line_no].strip() != str(self.subtitle_no+1):
                self.line_no += 1
        except IndexError:
            return '', -1
        data = ''
        while self.subtitle[self.line_no].strip() != '':
            data += self.subtitle[self.line_no]
            self.line_no += 1
        self.subtitle_no += 1
        return data, self.subtitle_no-1



