from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QMovie, QPalette, QColor, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDesktopWidget
import os
import sys
import time
import numpy as np
import win32api
import win32.lib.win32con as win32con
import cv2
import mediapipe as mp
from mediapipe.tasks import python
# import debugpy
import setting
import pygame
import sqlite3
status = ''
status_before = ''

class FaceRecognizer(QThread):
    init_recognizer_sgn = pyqtSignal()
    show_setting_sgn = pyqtSignal()

    MODEL_PATH = './model/face_landmarker_v2_with_blendshapes.task' #model path
    FADE_DURATION = 8
    SMILE_SCORE = 50 #happy rate 기본값
    SMILE_DURATION = 1 #스마일 지속 시간(1초)
    SAD_SCORE = 43 #unhappy rate 기본값
    SAD_DURATION = 1 #새드 지속 시간(1초)
    face_smile = [] #스마일 상태
    face_sad = [] #새드 상태
    show_face_point = False #카메라 얼굴인식 boundingbox 노출 여부
    show_log = False #카메라 얼굴인식 로그값
    MAX_FRAME_WIDTH = 10000 #카메라 최대 해상도 추출을 위한 초기값
    MAX_FRAME_HEIGHT = 10000 #카메라 최대 해상도 추출을 위한 초기값
    RESIZE_W = 100 #이모티콘 사이즈 크기 지정
    RESIZE_H = 100 #이모티콘 사이즈 크기 지정
    is_detect_face = False #FaceRecognizer 얼굴 인식 값
    faceTimeStamp = time.time() #얼굴인식 시점

    fade_idx = 0
    fade_list = np.linspace(0, 1, FADE_DURATION)
    is_fade_in = False
    is_fade_out = False

    def __init__(self, settingWindow):
        self.settingWindow = settingWindow

        super(FaceRecognizer, self).__init__()
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
        with open(self.MODEL_PATH, 'rb') as f:
            model = f.read()        
                
        options = FaceLandmarkerOptions(
            #base_options=python.BaseOptions(model_asset_path=self.MODEL_PATH),
            base_options=python.BaseOptions(model_asset_buffer=model),
            running_mode=VisionRunningMode.LIVE_STREAM,
            output_face_blendshapes=True, #해당 옵션을 활용하면 눈코입 등 상세정보를 받아올수있음
            result_callback=self.callbackResult
        )

        try:
            self.landmarker = FaceLandmarker.create_from_options(options)
        except Exception as e:
            win32api.MessageBox(0, f'facelandmarket init error - {e}', "Error", 16)
            self.exit()       
        
        self.timestamp = 0

        #카메라 최고 해상도로 찾기
        capture = cv2.VideoCapture(0)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.MAX_FRAME_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.MAX_FRAME_HEIGHT)
        self.MAX_FRAME_WIDTH = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.MAX_FRAME_HEIGHT = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))        

    def run(self):
        # debugpy.debug_this_thread() #쓰레드 동작이라 디버깅하기위해서 해당 옵션을 사용해야함. 상단 import도 주석제거필요함
        status = 'initial'
        status_before = 'initial'
        self.is_paused = False
        mp_drawing = mp.solutions.drawing_utils
        mp_face_detection = mp.solutions.face_detection
        face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.9) #검출에 성공한 것으로 간주할 얼굴의 검출 모델의 신뢰값
        cap = cv2.VideoCapture(0)
        fps = cap.get(cv2.CAP_PROP_FPS) #현재 webcam fps값
        y_point = ''
        x_point = ''
        SET_BOUNDARY = 10

        

        #카메라 프레임 최고 해상도로 변경하기
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.MAX_FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.MAX_FRAME_HEIGHT)

        self.init_recognizer_sgn.emit() #얼굴인식 라이브러리 초기화 완료
        while True:
            ret, frame = cap.read() #webcam으로부터 이미지 frame 인식
            if not ret: #webcam 인식 불가시 종료
                break
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #BGR to RGB
            frame = cv2.flip(frame, 1) #프레임 좌우 반전
            results = face_detection.process(frame) #얼굴탐지 실행
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) #RGB to BGR
            
            if results.detections: #얼굴이 탐지되는경우에만 표정인식 단계로 진행
                index = self.getMaxAreaIndex(results.detections) #탐지된 얼굴 중 넓이가 가장 큰 인덱스 선정

                # --------- START 얼굴 인식 흔들림 방지 (BOUNDARY 안에 들어오는 좌표값은 변경X ---------
                y_min_point = int(results.detections[index].location_data.relative_bounding_box.ymin * frame.shape[0]) #얼굴의 y축 좌표
                y_min_point = 0 if y_min_point < 0 else y_min_point #0보다 작으면 0
                x_min_point = int(results.detections[index].location_data.relative_bounding_box.xmin * frame.shape[1]) #얼굴의 x축 좌표
                x_min_point = 0 if x_min_point < 0 else x_min_point #0보다 작으면 0
                
                if y_point == '': #초기좌표가 설정이 안되있는 경우 처음 들어오는 초기값을 좌표로 설정
                    y_point = y_min_point
                elif y_min_point <= (y_point-SET_BOUNDARY) or y_min_point >= (y_point+SET_BOUNDARY): #들어오는 좌표가 boundary에 포함하지 않으면 좌표 변경
                    y_point = y_min_point

                if x_point == '': #초기좌표가 설정이 안되있는 경우 처음 들어오는 초기값을 좌표로 설정
                    x_point = x_min_point
                elif x_min_point <= (x_point-SET_BOUNDARY) or x_min_point >= (x_point+SET_BOUNDARY): #들어오는 좌표가 boundary에 포함하지 않으면 좌표 변경
                    x_point = x_min_point
                # --------- END 얼굴 인식 흔들림 방지 (BOUNDARY 안에 들어오는 좌표값은 변경X ---------

                #face poiint 체크
                if self.show_face_point: 
                    mp_drawing.draw_detection(frame, results.detections[index]) #화면에 face point 그리기
                
                #탐지된 얼굴만 추출하여 표정인식 동작
                frame_height = int(results.detections[index].location_data.relative_bounding_box.height*frame.shape[0])
                frame_width = int(results.detections[index].location_data.relative_bounding_box.width*frame.shape[1])
                np_array = frame[y_point:y_point+frame_height, x_point:x_point+frame_width]
                np_array = cv2.cvtColor(np_array, cv2.COLOR_BGR2RGB) #BGR to RGB
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np_array)

                #표정인식(face_landmark) 실행
                self.landmarker.detect_async(mp_image, self.timestamp)
                self.timestamp = self.timestamp + 1 # should be monotonically increasing, because in LIVE_STREAM mode

                
                if self.is_paused: #캠 중지 sleep 들어감  
                    emotion_time = selectDB()  # playtime 
                    if emotion_time[0][0] is None or emotion_time[0][1] is None: # 테이블에 데이터가 없을떄 
                        print("데이터가 없습니다.")
                    else:
                        if self.emotion == 'smile': # smile playtime
                            time.sleep(emotion_time[0][0])
                        elif self.emotion == 'sad':# sad playtime
                            time.sleep(emotion_time[0][1])
                        else:
                            print('없음')

                    self.resume() 

                #SMILE 값이 인식되는경우
                if len(self.face_smile) > 0:
                    if (fps*self.SMILE_DURATION) <= len(self.face_smile):
                        #print(f'smile : {status}', {setting.sw_toggle},{status_before},{status})
                        if status != 'smile':
                            if status_before != 'smile':                                
                                if setting.sw_toggle != False :
                                    cmd = {'type': 'message_send', 'data':{'emotionStatus': 'smile'}}
                                    setting.SettingWindow.emtionStatus_sad(self, cmd)
                                    self.settingWindow.upCnt('happy')  # 얼굴인식 cnt
                                    self.pause('smile')#  smile 캠 중지
                                    self.flash_effect(frame, 50, 100) # 번쩍
                                    frame = self.showBanner(frame, './images/bottom_rsquare01.png')  # 인식후 이미지
                                    
                                status_before = status 
                                status = 'smile'
                                
                    elif (fps*self.SMILE_DURATION*0.8571426) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/100.png', y_point, x_point)
                    elif (fps*self.SMILE_DURATION*0.7142855) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/80.png', y_point, x_point)                       
                    elif (fps*self.SMILE_DURATION*0.4285713) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/60.png', y_point, x_point)                       
                    elif (fps*self.SMILE_DURATION*0.4285713) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/40.png', y_point, x_point)                    
                    elif (fps*self.SMILE_DURATION*0.2857142) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/20.png', y_point, x_point)                       
                    elif (fps*self.SMILE_DURATION*0.1428571) <= len(self.face_smile):
                        frame = self.showIcon(frame, './images/happy/0.png', y_point, x_point)

                #SAD 값이 인식되는경우
                if len(self.face_sad) > 0: 
                    if (fps*self.SAD_DURATION) <= len(self.face_sad):
                        if status != 'sad':
                            if status_before != 'sad':
                                #print(f'sad : {status},{status_before}', {setting.sw_toggle})
                                if setting.sw_toggle != False :
                                    cmd = {'type': 'message_send', 'data': {'emotionStatus': 'sad'}}
                                    setting.SettingWindow.emtionStatus_sad(self, cmd)
                                    self.settingWindow.upCnt('unhappy')  # 얼굴인식 cnt                                    
                                    self.pause('sad')# sad 캠 중지 
                                    self.flash_effect(frame, 50, 100) # 번쩍
                                    frame = self.showBanner(frame, './images/bottom_rsquare01.png')  # 인식후 이미지

                                status_before = status    
                                status = 'sad' 
                            
                    elif (fps*self.SAD_DURATION*0.8571426) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/100.png', y_point, x_point)
                    elif (fps*self.SAD_DURATION*0.7142855) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/80.png', y_point, x_point)
                    elif (fps*self.SAD_DURATION*0.5714285) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/60.png', y_point, x_point)
                    elif (fps*self.SAD_DURATION*0.4285713) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/40.png', y_point, x_point)
                    elif (fps*self.SAD_DURATION*0.2857142) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/20.png', y_point, x_point)
                    elif (fps*self.SAD_DURATION*0.1428571) <= len(self.face_sad):
                        frame = self.showIcon(frame, './images/unhappy/0.png', y_point, x_point)

                #SMILE와 SAD가 아닌경우 무표정 처리 + 표정인식값이 True일때만
                if len(self.face_smile) == 0 and len(self.face_sad) == 0 and self.is_detect_face:
                    if status != 'ready':
                        time.sleep(0.1)
                        if setting.sw_toggle != False :                            
                            cmd = {'type': 'message_send', 'data':{'emotionStatus': 'ready'}}
                            setting.SettingWindow.emtionStatus_sad(self, cmd)
                        status = 'ready'
                        status_before = 'ready'
                        
                    frame = self.showIcon(frame, './images/ready.png', y_point, x_point)

                else :
                    if (time.time()-self.faceTimeStamp) > 1.0: #얼굴인식이 1.2초이상 이루어지지 않을 시 banner fade in
                        self.is_fade_in = True #좌측상단 이미지 fade_in trigger
                    #print("없음")

                #SMILE, SAD 아니고, 표정인식이 안되는경우에는 좌측상단이미지 노출
                # if len(self.face_smile) == 0 and len(self.face_sad) == 0 and self.is_detect_face == False:
                #     if (time.time()-self.faceTimeStamp) > 1.2: #얼굴인식이 1.2초이상 이루어지지 않을 시 banner fade in
                #         self.is_fade_in = True #좌측상단 이미지 fade_in trigger
                    
                    
            else: #face not found
                if status != 'wait':
                    time.sleep(0.1)
                    if setting.sw_toggle != False :
                        cmd = {'type': 'message_send', 'data':{'emotionStatus': 'wait'}}
                        setting.SettingWindow.emtionStatus_sad(self, cmd)
                        
                    status_before = status 
                    status = 'wait'  
                    
                if self.show_log: #로그 노출 허용하면 print
                    print('face not found')

                # print(time.time()-self.faceTimeStamp)
                if (time.time()-self.faceTimeStamp) > 1.0: #얼굴인식이 1.2초이상 이루어지지 않을 시 banner fade in
                    self.is_fade_in = True #좌측상단 이미지 fade_in trigger
            
            if self.is_fade_in and self.is_fade_out == False:
                # print(f'in : {self.fade_idx}')
                if self.fade_idx < (len(self.fade_list)-1):
                    frame = self.applyFade(frame, self.fade_list[self.fade_idx])
                    self.fade_idx += 1
                else:
                    frame = self.applyFade(frame, self.fade_list[self.fade_idx])
            
            if self.is_fade_out:
                # print(f'out : {self.fade_idx}')
                if self.fade_idx > 0:
                    frame = self.applyFade(frame, self.fade_list[self.fade_idx])
                    self.fade_idx -= 1
                else:
                    self.is_fade_in = False
                    self.is_fade_out = False

            cv2.namedWindow('SIM Mobile Communication FaceRecognizer', cv2.WINDOW_NORMAL) #카메라창 이름부여, 화면 속성변경
            cv2.imshow('SIM Mobile Communication FaceRecognizer', frame)
            cv2.setWindowProperty('SIM Mobile Communication FaceRecognizer', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN) #카메라창 전체화면으로 변경

            key_code = cv2.waitKeyEx(1)
            if key_code == 27: #[ESC] 키를 누르면 종료
                answer = win32api.MessageBox(0, 'Are you sure you want to exit the program?', 'Notice', win32con.MB_YESNO | win32con.MB_ICONQUESTION)
                if answer == win32con.IDYES:
                    self.exit()
                    break
            # elif key_code == 0x730000: #F4 키를 누르면 번쩍 섬광 효과 (0.05초)
            #     self.flash_effect(frame, 50)
            elif key_code == 7471104: #F3 키를 누르면 얼굴 포인트 노출 on/off
                self.show_face_point = True if self.show_face_point == False else False
            elif key_code == 7405568: #F2 키를 누르면 로그 노출 on/off
                self.show_log = True if self.show_log == False else False
            elif key_code == 7340032: #F1 키를 누르면 환경설정 실행
                answer = win32api.MessageBox(0, 'Are you sure you want to enter Setting?', 'Notice', win32con.MB_YESNO | win32con.MB_ICONQUESTION)
                if answer == win32con.IDYES:
                    self.show_setting_sgn.emit()
        
        cap.release()
        cv2.destroyAllWindows()
    
    def applyFade(self, frame, alpha):
        if alpha > 0.8: #banner 투명도 조절
            alpha = 0.8
        mask = self.createMask(frame)
        added = cv2.addWeighted(mask, alpha, frame, 1 - alpha, 1)
        return added

    def createMask(self, frame):
        sticker = cv2.imread("./images/top_rsquare01.png", cv2.IMREAD_UNCHANGED)
        sticker = cv2.resize(sticker, frame.shape[1::-1])

        mask = sticker[:, :, 3]
        mask_inv = cv2.bitwise_not(mask)
        sticker = cv2.cvtColor(sticker, cv2.COLOR_BGRA2BGR)
        roi = frame[0 : sticker.shape[0], 0 : sticker.shape[1]]

        masked_fg = cv2.bitwise_and(sticker, sticker, mask=mask)
        masked_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
        added = cv2.add(masked_fg, masked_bg)
        return added

    def pause(self,emotion_time): 
        self.is_paused = True
        self.emotion = emotion_time
        #print(emotion)
        
    def resume(self): 
        self.is_paused = False    

    def flash_effect(self, frame, flash_duration_ms=500, fadeout_duration_ms=500):
        pygame.mixer.init()
        pygame.mixer.music.load("./sound/click.mp3")
        pygame.mixer.music.play()
                
        flash_frame = np.ones_like(frame) * 255
        # 플래시 효과를 적용할 시간 (플래시 지속시간)
        flash_time = cv2.getTickCount() + flash_duration_ms * cv2.getTickFrequency() / 1000

        while cv2.getTickCount() < flash_time:
            # 화면을 흰색으로 채우기
            cv2.imshow('SIM Mobile Communication FaceRecognizer', flash_frame)
            # cv2.waitKey(1)

        # 플래시 효과가 끝난 뒤 fade-out 효과 주기
        start_time = cv2.getTickCount()
        while (cv2.getTickCount() - start_time) < fadeout_duration_ms * cv2.getTickFrequency() / 1000:
            alpha = 1.0 - ((cv2.getTickCount() - start_time) / (fadeout_duration_ms * cv2.getTickFrequency() / 1000))
            blended_frame = cv2.addWeighted(frame, alpha, flash_frame, 1 - alpha, 0)
            cv2.imshow('SIM Mobile Communication FaceRecognizer', blended_frame)
            cv2.waitKey(1)

        # 원본 프레임으로 돌아가기
        cv2.imshow('SIM Mobile Communication FaceRecognizer', frame)
    
    #탐지되는 얼굴중 boundbox의 넓이가 가장 큰 index 구하기
    def getMaxAreaIndex(self, results):
        max_index = max(range(len(results)), key=lambda i: results[i].location_data.relative_bounding_box.width * results[i].location_data.relative_bounding_box.height)
        return max_index

    def showIcon(self, frame, img_path, y, x):
        self.is_fade_out = True #이모티콘이 노출시 좌측상단 이미지 fade_out trigger
        self.faceTimeStamp = time.time() #얼굴인식시점 기록

        img_fg = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        img_fg = cv2.resize(img_fg, (self.RESIZE_W, self.RESIZE_H)) #image size 100으로 고정

        # 알파 채널을 이용해서 마스크와 역마스크 생성
        _, mask = cv2.threshold(img_fg[:,:,3], 128, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)

        # 전경 영상 크기로 배경 영상에서 ROI 잘라내기
        img_fg = cv2.cvtColor(img_fg, cv2.COLOR_BGRA2BGR)
        h, w = img_fg.shape[:2]

        y_point = 0 if (y-h) <= 0 else (y-h) #boundbox y좌표에서 ROI 크기를 뺀 좌표가 0보다 작으면 0으로 처리
        x_point = 0 if (x-w) <= 0 else (x-w)

        roi = frame[y_point:y_point+self.RESIZE_W, x_point:x_point+self.RESIZE_H]

        # 마스크 이용해서 오려내기
        masked_fg = cv2.bitwise_and(img_fg, img_fg, mask=mask)
        masked_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)

        # 이미지 합성
        added = cv2.add(masked_fg, masked_bg)
        frame[y_point:y_point+self.RESIZE_W, x_point:x_point+self.RESIZE_H] = added
        return frame
    
    def showBanner(self, frame, img_path):
        img_fg = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        img_fg = cv2.resize(img_fg, (self.MAX_FRAME_WIDTH, self.MAX_FRAME_HEIGHT)) #image size 해상도와 맞춤

        # 알파 채널을 이용해서 마스크와 역마스크 생성
        _, mask = cv2.threshold(img_fg[:,:,3], 128, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)

        # 전경 영상 크기로 배경 영상에서 ROI 잘라내기
        img_fg = cv2.cvtColor(img_fg, cv2.COLOR_BGRA2BGR)
        h, w = img_fg.shape[:2]
        roi = frame[0:0+h, 0:0+w]

        # 마스크 이용해서 오려내기
        masked_fg = cv2.bitwise_and(img_fg, img_fg, mask=mask)
        masked_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)

        # 이미지 합성
        added = cv2.add(masked_fg, masked_bg)
        frame = cv2.addWeighted(added, 0.8, frame, 0.2, 1) #투명도 조절
        return frame
    
    def callbackResult(self, result, output_image, timestamp_ms):
        try:
            self.is_detect_face = True if len(result.face_blendshapes) > 0 else False #얼굴이 나타나면 True

            if self.is_detect_face: # ==================== found =================== 
                # --------------- SMILE CHECK START-----------------
                mouth_smile_left = result.face_blendshapes[0][44].score
                mouth_smile_right = result.face_blendshapes[0][45].score
                face_smile = (mouth_smile_left + mouth_smile_right) / 2 * 100

                if face_smile > self.SMILE_SCORE:
                    self.face_sad.clear() # SAD clear 동시에 두개 상태가 발생할수없음
                    self.face_smile.append(f'smlie : {face_smile}')
                else:
                    self.face_smile.clear()
                # --------------- SMILE CHECK END-----------------

                # ---------------- SAD CHECK START -----------------
                #눈썹 하강 50%
                brow_down_left =  result.face_blendshapes[0][1].score
                brow_down_right =  result.face_blendshapes[0][2].score
                brow_down = (brow_down_left + brow_down_right) / 2 * 100

                #눈 물결 모양(수축) 50%
                eye_squint_left = result.face_blendshapes[0][19].score
                eye_squint_right = result.face_blendshapes[0][20].score
                eye_squint = (eye_squint_left + eye_squint_right) / 2 * 100

                #입꼬리 하강
                mouth_frown_left = result.face_blendshapes[0][30].score
                mouth_frown_right = result.face_blendshapes[0][31].score
                mouth_frown = (mouth_frown_left + mouth_frown_right) / 2 * 100

                face_sad_A = (brow_down*0.5) + (eye_squint*0.5)
                face_sad_B = (mouth_frown*0.5) + (eye_squint*0.5)
                face_sad_C = (mouth_frown*0.5) + (brow_down*0.5)

                if face_sad_A >= self.SAD_SCORE:
                    self.face_smile.clear() #SMILE SAD 동시에 두개 상태가 발생할수없음
                    self.face_sad.append(f'sad : {face_sad_A}')
                elif face_sad_B >= self.SAD_SCORE:
                    self.face_smile.clear() #SMILE SAD 동시에 두개 상태가 발생할수없음
                    self.face_sad.append(f'sad : {face_sad_B}')
                elif face_sad_C >= self.SAD_SCORE:
                    self.face_smile.clear() #SMILE SAD 동시에 두개 상태가 발생할수없음
                    self.face_sad.append(f'sad : {face_sad_C}')
                else:
                    self.face_sad.clear()
                # ---------------- SAD CHECK END -----------------

                # print(f'smile : {face_smile}  sad : {face_sad}')
                if self.show_log: #로그 노출 허용하면 print
                    print(f'smile : {face_smile}  sad_A : {face_sad_A}  sad_B : {face_sad_B}  sad_C : {face_sad_C}')
                    
            else:# smlie , sad 인식후 얼굴인식이 안될때 초기화
                self.face_smile.clear()  
                self.face_sad.clear() 
                #print("얼굴인식안댐")   

        except Exception as e:
            print('예외가 발생했습니다.', e)

    def exit(self):
        pid = os.getpid()
        os.kill(pid, 2)

    def stop(self):
        self.quit()
        self.wait(3000) #종료 후 3초 대기

class SoundThread(QThread):

    def __init__(self, parent):

        super().__init__(parent)
        self.power = True

    def run(self):
        pygame.mixer.init()
        pygame.mixer.music.load("./sound/click.mp3")
        pygame.mixer.music.play()
        #playsound.playsound("./sound/click.mp3")    # 찰칵소리

    def stop(self):
        self.power = False
        self.quit()
        self.terminate()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.settingWindow = setting.SettingWindow(self)
        self.face_recognizer = FaceRecognizer(self.settingWindow)
        self.face_recognizer.init_recognizer_sgn.connect(self.initRecognize)
        self.face_recognizer.show_setting_sgn.connect(self.showSetting)

    def initUI(self):
        self.resize(500, 500) #화면사이즈 500x500
        self.center_to_screen() #화면 중앙으로 이동
        self.setWindowIcon(QIcon('./images/logo.ico')) #로고 부여
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint) #제목 표시줄 제거 및 최상위 윈도우 설정
        self.setWindowTitle('SIM Mobile Communication FaceRecognizer')
        self.setWindowFlags(Qt.WindowStaysOnTopHint) #최상단에 보이게하기

        #배경색 흰색으로 변경
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(Qt.white))
        self.setPalette(palette)

        self.loading_label = QLabel(self)
        self.loading_movie = QMovie('./images/loading.gif')
        self.loading_label.setMovie(self.loading_movie)
        self.loading_label.setAlignment(Qt.AlignCenter)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.loading_label)
        self.setCentralWidget(central_widget)

    def showEvent(self, event):
        super().showEvent(event)
        self.loading_movie.start()
        self.face_recognizer.setTerminationEnabled(True)
        self.face_recognizer.start()
        
        time.sleep(4)
        self.settingWindow.show()
        self.settingWindow.showMinimized()

    def center_to_screen(self):
        frame_info = self.frameGeometry()
        display_center = QDesktopWidget().availableGeometry().center()
        frame_info.moveCenter(display_center)
        self.move(frame_info.topLeft())
    
    def initRecognize(self):
        print('init_face_recognizer complete')
        self.hide()
    
    @pyqtSlot()
    def showSetting(self):
        print('show setting')
        self.settingWindow.showNormal()
        self.settingWindow.activateWindow()

def selectDB(): #playtime 조회
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql = "SELECT MAX(s_smileplaytime), MAX(s_sadplaytime) FROM setting"
    cursor.execute(sql)
    conn.commit()
    db_list = cursor.fetchall()
    conn.close()
    return db_list        
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())