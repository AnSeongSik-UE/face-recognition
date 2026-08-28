import sqlite3
import sys
import time,base64,json,os
from PyQt5.QtCore import QThread, QUrl, pyqtSignal,Qt
from PyQt5.QtWidgets import QDialog, QMessageBox, QStyle, QGraphicsPixmapItem, QGraphicsScene, QFileDialog, QGraphicsTextItem, QApplication
from PyQt5 import uic
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
import setting

settingDetail_ui = uic.loadUiType("./ui/setting-detail.ui")[0]
class SettingDetail(QDialog, settingDetail_ui,):
    def __init__(self, uuid, socketList, soc_port):
        self.uuid = uuid
        self.saved = 1          # 1 저장됨 / 0 저장안됨
        self.WRType = 'w'
        self.previewRunning = 0 # 0 정지 / 1 실행
        self.receiveStanby = False #파일 수신 대기중
        self.smilePlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.sadPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.socketList = socketList
        self.soc_port = soc_port
        self.fontDB = QFontDatabase()
        self.fontDB.addApplicationFont('./font/AxisStd-Regular.otf')
        self.fontDB.addApplicationFont('./font/SamsungOneItalicLatin-600_v1.1.ttf')
        self.fontDB.addApplicationFont('./font/SamsungOneKoreanOTF 600.otf')
        self.fontDB.addApplicationFont('./font/SamsungOneSCN-600_20160824.ttf')

        super().__init__()
        self.setupUi(self)

        # 위치, 속도 기본값 index
        self.sd_locate.setCurrentIndex(1)
        self.sd_speed.setCurrentIndex(1)
        self.defaultPreview()
        self.sd_textPreviewBtn.clicked.connect(self.playTextPreview)    # 텍스트프리뷰 재생

        self.loadProcess(uuid)
        self.setWindowFlags(Qt.WindowStaysOnTopHint) #최상단에 보이게하기
        self.sd_tab.setCurrentIndex(0)

        #DB연결 확인
        try:
            conn = sqlite3.connect('db.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM setting")
            conn.close()
        except:
            QMessageBox().warning(self, 'Error', "Wrong 'db.db' file.")
            sys.exit(0)

        self.sd_waitRadio.clicked.connect(self.checkWR)         # wait ready 상태 체크
        self.sd_readyRadio.clicked.connect(self.checkWR)

        # 변경사항 감지 후 저장여부 질문
        self.sd_deviceName.textChanged.connect(self.isChanged)
        self.sd_textEdit.textChanged.connect(self.isChanged)
        self.sd_fontSize.valueChanged.connect(self.isChanged)
        self.sd_fontCombo.currentIndexChanged.connect(self.isChanged)
        self.sd_fontColor.currentIndexChanged.connect(self.isChanged)
        self.sd_locate.currentIndexChanged.connect(self.isChanged)
        self.sd_speed.currentIndexChanged.connect(self.isChanged)
        self.sd_direction.currentIndexChanged.connect(self.isChanged)


# sMedia
#############################################################################
        # 변경사항 감지 후 저장여부 질문
        self.sd_smileFile.textChanged.connect(self.isChanged)
        self.sd_sadFile.textChanged.connect(self.isChanged)

        # 영상길이 설정
        self.sd_smilePlayTime.valueChanged.connect(lambda : self.setDuration('smile'))
        self.sd_sadPlayTime.valueChanged.connect(lambda : self.setDuration('sad'))

        self.sd_findSmile.clicked.connect(lambda : self.findMedia('smile'))      # 웃는상태 동영상, 이미지 경로 설정
        self.sd_findSad.clicked.connect(lambda : self.findMedia('sad'))          # 슬픈상태 동영상, 이미지 경로 설정
        
        # 재생아이콘
        self.sd_smilePlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.sd_smilePlay.clicked.connect(lambda : self.play('smile'))
        self.sd_sadPlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.sd_sadPlay.clicked.connect(lambda : self.play('sad'))
        
        # 재생슬라이더
        self.sd_smileSlider.setRange(0, 0)
        self.sd_smileSlider.sliderMoved.connect(self.setSmilePosition)
        self.sd_sadSlider.setRange(0, 0)
        self.sd_sadSlider.sliderMoved.connect(self.setSadPosition)

        # happy 영상관련 세팅
        self.smilePlayer.setVideoOutput(self.sd_smileVideo)
        self.smilePlayer.stateChanged.connect(lambda : self.mediaStateChanged('smile'))
        self.smilePlayer.positionChanged.connect(self.smilePositionChanged)
        self.smilePlayer.durationChanged.connect(lambda : self.durationChanged('smile'))
        self.smilePlayer.error.connect(lambda : self.handleError('smile'))

        # unhappy 영상관련 세팅
        self.sadPlayer.setVideoOutput(self.sd_sadVideo)
        self.sadPlayer.stateChanged.connect(lambda : self.mediaStateChanged('sad'))
        self.sadPlayer.positionChanged.connect(self.sadPositionChanged)
        self.sadPlayer.durationChanged.connect(lambda : self.durationChanged('sad'))
        self.sadPlayer.error.connect(lambda : self.handleError('sad'))
#############################################################################
# eMedia
        # Save 버튼
        self.sd_saveBtn.clicked.connect(lambda: self.saveBtnMessage(socketList,self.sd_smileFile.text(), self.sd_sadFile.text(), soc_port))
        
        # happy, unhappy 미디어 전송버튼
        self.sd_smileApplyBtn.clicked.connect(lambda: self.sd_apply_smileFile(socketList,self.sd_smileFile.text(), self.sd_sadFile.text(), soc_port))
        self.sd_sadApplyBtn.clicked.connect(lambda: self.sd_apply_sadFile(socketList,self.sd_smileFile.text(), self.sd_sadFile.text(), soc_port))
        
        # Close 버튼
        self.sd_closeBtn.clicked.connect(self.backToSetting)

        # 폰트 설정
        self.sd_tab.setFont(QFont('굴림', 9))
        self.sd_saveBtn.setFont(QFont('굴림', 9))
        self.sd_closeBtn.setFont(QFont('굴림', 9))

    # 프리뷰 기본배경
    def defaultPreview(self):
        pix = QPixmap(".\\ui\\previewBg.png")
        item = QGraphicsPixmapItem(pix.scaled(329, 459))
        scene = QGraphicsScene(self)
        scene.addItem(item)
        self.sd_textPreview.setScene(scene)
    
    def isChanged(self):
        print('isChanged')
        self.saved = 0

    def checkWR(self):
        if self.sd_waitRadio.isChecked():
            if self.saved == 0:
                buttonReply = QMessageBox.warning(self, 'Warning', 'Your changes not saved.\nSave your changes?', QMessageBox.Yes, QMessageBox.No)
                if buttonReply == QMessageBox.Yes:
                    self.saveProcess(self.socketList,self.soc_port)
            self.WRType = 'w'

        elif self.sd_readyRadio.isChecked():
            if self.saved == 0:
                buttonReply = QMessageBox.warning(self, 'Warning', 'Your changes not saved.\nSave your changes?', QMessageBox.Yes, QMessageBox.No)
                if buttonReply == QMessageBox.Yes:
                    self.saveProcess(self.socketList,self.soc_port)
            self.WRType = 'r'

        self.loadProcess(self.uuid)
        self.saved = 1

    #Run to Preview
    def playTextPreview(self):
        if self.previewRunning == 0:
            print('run')
            self.sd_textPreviewBtn.setText('Stop')
            txt = self.sd_textEdit.toPlainText()

            #font selected
            if self.sd_fontCombo.currentIndex() == 0:
                font = QFont('AXIS Std R', self.sd_fontSize.value())
            elif self.sd_fontCombo.currentIndex() == 1:
                font = QFont('SamsungOneItalicLatin 600', self.sd_fontSize.value())
            elif self.sd_fontCombo.currentIndex() == 2:
                font = QFont('SamsungOneKoreanOTF 600', self.sd_fontSize.value())
            elif self.sd_fontCombo.currentIndex() == 3:
                font = QFont('SamsungOneSCN 600', self.sd_fontSize.value())
            
            # sd_fontColor    0 SIM BLUE / 1 SIM GRAY / 2 SIM BLACK / 3 SIM WHITE
            if self.sd_fontColor.currentIndex() == 0:
                Red = 98
                Green = 158
                Blue = 199
            elif self.sd_fontColor.currentIndex() == 1:
                Red = 107
                Green = 108
                Blue = 108
            elif self.sd_fontColor.currentIndex() == 2:
                Red = 0
                Green = 0
                Blue = 0
            elif self.sd_fontColor.currentIndex() == 3:
                Red = 255
                Green = 255
                Blue = 255

            x = self.sd_textPreview.geometry().width()
            y = self.sd_textPreview.geometry().height()            
            loc = self.sd_locate.currentIndex()         # 0 상단 / 1 중단 / 2 하단
            direct = self.sd_direction.currentIndex()   # 0 좌로 / 1 우로 / 2 위로 / 3 아래로
            # rotate = 반복위치, a = x 시작점, b = y 시작점, c = x 변동값, d = y 변동값
            if loc == 0:
                if direct == 0:
                    rotate = x
                    a = 0
                    b = 0
                    c = 1
                    d = 0
                elif direct == 1:
                    rotate = x
                    a = x
                    b = 0
                    c = -1
                    d = 0
                elif direct == 2:
                    rotate = y
                    a = 0
                    b = y
                    c = 0
                    d = -1
                elif direct == 3:
                    rotate = y
                    a = 0
                    b = 0
                    c = 0
                    d = 1
            elif loc == 1:
                if direct == 0:
                    rotate = x
                    a = 0
                    b = y/2 - font.pointSize()*2
                    c = 1
                    d = 0
                elif direct == 1:
                    rotate = x
                    a = x
                    b = y/2 - font.pointSize()*2
                    c = -1
                    d = 0
                elif direct == 2:
                    rotate = y
                    a = x/2 - font.pointSize()*2
                    b = y
                    c = 0
                    d = -1
                elif direct == 3:
                    rotate = y
                    a = x/2 - font.pointSize()*2
                    b = 0
                    c = 0
                    d = 1
            elif loc == 2:
                if direct == 0:
                    rotate = x
                    a = 0
                    b = y - font.pointSize()*4
                    c = 1
                    d = 0
                elif direct == 1:
                    rotate = x
                    a = x
                    b = y - font.pointSize()*4
                    c = -1
                    d = 0
                elif direct == 2:
                    rotate = y
                    a = x - font.pointSize()*4
                    b = y
                    c = 0
                    d = -1
                elif direct == 3:
                    rotate = y
                    a = x- font.pointSize()*4
                    b = 0
                    c = 0
                    d = 1

            #speed selected
            if self.sd_speed.currentIndex() == 0:
                spd = 0.01
            elif self.sd_speed.currentIndex() == 1:
                spd = 0.005
            elif self.sd_speed.currentIndex() == 2:
                spd = 0.001

            self.previewRunning = 1
            self.previewThread = PreviewThread(self, txt, font, Red, Green, Blue, rotate, a, b, c, d, spd)
            self.previewThread.changeTextPreview.connect(self.sd_textPreview.setScene)
            self.previewThread.start()

        elif self.previewRunning == 1:
            print('stop')
            self.previewThread.stop()
            self.previewRunning = 0
            self.sd_textPreviewBtn.setText('Preview')

    def closeEvent(self, event):
        print('toggle_True')
        self.changedName = self.sd_deviceName.text()
        setting.SettingWindow.toggle_True(self)  

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()                        # setting으로 복귀
            setting.SettingWindow.toggle_True(self)
            
    def sd_apply_smileFile(self,socketList,sand_smilefile,sand_sadfile,soc_port):
        try:
            if sand_smilefile != None:
                print(sand_smilefile)
                self.send_file_to_client(socketList, sand_smilefile, soc_port, 'happy')
                time.sleep(3)
        except FileNotFoundError as err:
            print(f'FileNotFoundError1 - {err}')

    def sd_apply_sadFile(self,socketList,sand_smilefile,sand_sadfile,soc_port):
        try: 
            if sand_sadfile != None:
                self.send_file_to_client(socketList, sand_sadfile, soc_port, 'unhappy')
                time.sleep(3)
        except FileNotFoundError as err:
            print(f'FileNotFoundError2 - {err}')

    def saveBtnMessage(self,socketList,sand_smilefile,sand_sadfile,soc_port):
        buttonReply = QMessageBox.information(self, 'Info', 'Are you sure to save your changes?', QMessageBox.Yes, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            temp = self.saveProcess(socketList,soc_port)
            if temp != 99:
                QMessageBox.information(self, 'Info', 'Your changes have been saved.')
        elif buttonReply == QMessageBox.No:
            QMessageBox.information(self, 'Info', 'Save canceled.')

    def switchStanby(self):
        if self.receiveStanby:
            self.receiveStanby = False
        else:
            self.receiveStanby = True

    def backToSetting(self):
        if self.saved == 0:
            buttonReply = QMessageBox.warning(self, 'Warning', 'Your changes not saved.\nReturn to the previous window?', QMessageBox.Yes, QMessageBox.No)
            if buttonReply == QMessageBox.Yes:
                self.close()                        # setting으로 복귀
                setting.SettingWindow.toggle_True(self)
        elif self.saved == 1:
                self.close()                        # setting으로 복귀
                setting.SettingWindow.toggle_True(self)
    
    def chunk_string(self, string, chunk_size):
        return (string[0+i:chunk_size+i] for i in range(0, len(string), chunk_size))
    
    def send_file_to_client(self, socketList, sd_smileFile, soc_port, emotion):
        print(f"socketList : {socketList}")
        print(f"sd_smileFile : {sd_smileFile}")
        print(f"soc_port : {soc_port}")
           
        file_path = sd_smileFile # 전송할 파일 경로
        file_size = os.path.getsize(file_path)  # 파일 크기
        file_name = os.path.basename(file_path)

        if file_size > 10 * 1024 * 1024:  # 10MB
            print("파일 크기가 10MB 이상입니다. 파일을 분할해서 전송하세요.")
        else:
            try:
                print(f"파일 전송을 진행합니다. 파일사이즈 {file_size}")
                self.sd_smileApplyBtn.setEnabled(False)
                self.sd_sadApplyBtn.setEnabled(False)

                socket_obj = socketList[soc_port]
                json_message = json.dumps({ 'type': 'file_start', 'data' :{ 'method': 'file', 'file_name': file_name, 'emotion' : emotion} })
                socket_obj.sendall(json_message.encode('utf-8'))  # Send 'file_start'
                self.receiveStanby = True
                print("파일 전송 대기중...")
                start_time = time.time()
                
                while self.receiveStanby: #파일 전송 대기중에는 무한루프
                    current_time = time.time()
                    elapsed_time = current_time - start_time #wait 시간 계산(초)

                    if self.receiveStanby == False:
                        print(f"클라이언트[{soc_port}] 수신 대기 완료")
                        break
                    
                    if elapsed_time >= 20: #wait 시간(20초)를 초과할 경우 파일 전송 대기 실패
                        fail_message = "{'type':'file_fail'}"
                        print(fail_message)
                        self.sd_smileApplyBtn.setEnabled(True)
                        self.sd_sadApplyBtn.setEnabled(True)
                        socket_obj.sendall(fail_message.encode('utf-8'))  # Send 'fail_message'
                        QMessageBox.information(self,'Info', 'Sending failed.')
                        break

                count = 0
                with open(file_path, 'rb') as file_data: #file_path에 위치한 파일 열기
                    try:
                        content = file_data.read() #파일 전체 읽기
                        encoded_content = base64.b64encode(content).decode('utf-8') #base64로 인코딩
                        chunks = self.chunk_string(encoded_content, 1024) #base64로 인코딩 된 text를 1024 크기로 자름
                        for chunk in chunks:
                            print(f"{count} {chunk}" + "\n\n")
                            socket_obj.sendall(chunk.encode('utf-8'))
                            time.sleep(0.005)
                            count+=1
                    except Exception as ex:
                        QMessageBox().warning(self, 'Warning(1)', str(ex))
  
                end_message = "{'type':'file_end'}"
                socket_obj.sendall(end_message.encode('utf-8'))  # Send 'file_end'
                print("전송완료 %s" % file_path)
                self.sd_smileApplyBtn.setEnabled(True)
                self.sd_sadApplyBtn.setEnabled(True)
                QMessageBox.information(self, 'Info', 'Sent successfully.')
                self.receiveStanby = True
            except Exception as ex:
                QMessageBox().warning(self, 'Warning(2)', str(ex))
# sMedia
####################################################################
    def setDuration(self, status):
        if status == "smile":
            self.sd_smileSlider.setRange(0, self.sd_smilePlayTime.value()*1000)
        elif status == "sad":
            self.sd_sadSlider.setRange(0, self.sd_sadPlayTime.value()*1000)
        self.isChanged()

    def findMedia(self, status):
        path = QFileDialog.getOpenFileName(self, "Select Media") # 전체파일
        if path[0]:
            file_size = os.path.getsize(path[0])
            if file_size <= 10485760:               # 10메가 제한
                self.setupMedia(status, path[0])
            else:
                QMessageBox.warning(self, 'Error', "Cannot be upload larger than 10MB.")

    def play(self, status):
        if status == "smile":
            if self.smilePlayer.state() == QMediaPlayer.PlayingState:
                self.smilePlayer.pause()
            else:
                self.smilePlayer.play()
        elif status == "sad":
            if self.sadPlayer.state() == QMediaPlayer.PlayingState:
                self.sadPlayer.pause()
            else:
                self.sadPlayer.play()

    def mediaStateChanged(self, status):
        if status == "smile":
            if self.smilePlayer.state() == QMediaPlayer.PlayingState:
                self.sd_smilePlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            else:
                self.sd_smilePlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        elif status == "sad":
            if self.sadPlayer.state() == QMediaPlayer.PlayingState:
                self.sd_sadPlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            else:
                self.sd_sadPlay.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def smilePositionChanged(self, position):
        self.sd_smileSlider.setValue(position)
        if self.sd_smileSlider.value()/1000 >= self.sd_smilePlayTime.value():
            self.smilePlayer.pause()
            self.smilePlayer.setPosition(0)

    def sadPositionChanged(self, position):
        self.sd_sadSlider.setValue(position)
        if self.sd_sadSlider.value()/1000 >= self.sd_sadPlayTime.value():
            self.sadPlayer.pause()
            self.sadPlayer.setPosition(0)

    def durationChanged(self, status):
        if status == "smile":
            self.sd_smileSlider.setRange(0, self.sd_smilePlayTime.value()*1000)
        elif status == "sad":
            self.sd_sadSlider.setRange(0, self.sd_sadPlayTime.value()*1000)

    def setSmilePosition(self, position):
        self.smilePlayer.setPosition(position)

    def setSadPosition(self, position):
        self.sadPlayer.setPosition(position)

    def handleError(self, status):
        if status == "smile":
            QMessageBox.warning(self, 'Error', "Please install K-Lite Codec.\nMedia file not found.")
            self.sd_smileFile.setText('Target_Contents_Folder')

        elif status == "sad":
            QMessageBox.warning(self, 'Error', "Please install K-Lite Codec.\nMedia file not found.")
            self.sd_sadFile.setText('Target_Contents_Folder')
    
    def setupMedia(self, status, path):
        if status == "smile":
            self.sd_smileFile.setText(path)
            self.smilePlayer.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.sd_smilePlay.setEnabled(True)

        elif status == "sad":
            self.sd_sadFile.setText(path)
            self.sadPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.sd_sadPlay.setEnabled(True)
        
###################################################################
# eMedia
    def loadProcess(self, uuid):
        data = selectDB(uuid)
        self.sd_deviceName.setText(data[0][1])
        self.sd_uuid.setText(uuid)

        if self.WRType == 'w':
            self.sd_textEdit.setPlainText(data[0][3])
            self.sd_fontSize.setValue(data[0][4])
            self.sd_fontCombo.setCurrentIndex(data[0][5])
            self.sd_fontColor.setCurrentIndex(data[0][6])
            self.sd_locate.setCurrentIndex(data[0][7])
            self.sd_speed.setCurrentIndex(data[0][8])
            self.sd_direction.setCurrentIndex(data[0][9])
        elif self.WRType == 'r':
            self.sd_textEdit.setPlainText(data[0][10])
            self.sd_fontSize.setValue(data[0][11])
            self.sd_fontCombo.setCurrentIndex(data[0][12])
            self.sd_fontColor.setCurrentIndex(data[0][13])
            self.sd_locate.setCurrentIndex(data[0][14])
            self.sd_speed.setCurrentIndex(data[0][15])
            self.sd_direction.setCurrentIndex(data[0][16])

        self.sd_smilePlayTime.setValue(data[0][18])
        self.sd_smileFile.setText(data[0][19])
        if data[0][19] != 'Target_Contents_Folder':
            self.setupMedia('smile', data[0][19])
        self.sd_sadPlayTime.setValue(data[0][21])
        self.sd_sadFile.setText(data[0][22])
        if data[0][22] != 'Target_Contents_Folder':
            self.setupMedia('sad', data[0][22])

    def saveProcess(self,socketList,soc_port):
        print('saved')
        
        self.saved = 1
        if self.sd_tab.currentIndex() == 0:
            updateTxtDB(self.WRType,
                        self.sd_deviceName.text(),
                        self.sd_textEdit.toPlainText(),
                        self.sd_fontSize.value(),
                        self.sd_fontCombo.currentIndex(),
                        self.sd_fontColor.currentIndex(),
                        self.sd_locate.currentIndex(),
                        self.sd_speed.currentIndex(),
                        self.sd_direction.currentIndex(),
                        self.sd_uuid.text()
                        )

            WRtype = self.WRType
            deviceName = self.sd_deviceName.text()          

            content = self.sd_textEdit.toPlainText()
            size = self.sd_fontSize.value()

            font = self.sd_fontCombo.currentIndex()
            font = self.sd_fontCombo.itemText(font)

            color = self.sd_fontColor.currentIndex()
            color = self.sd_fontColor.itemText(color)

            locate = self.sd_locate.currentIndex()
            locate = self.sd_locate.itemText(locate)
            
            speed = self.sd_speed.currentIndex()
            speed = self.sd_speed.itemText(speed)
            
            direction = self.sd_direction.currentIndex()
            direction = self.sd_direction.itemText(direction)
            
            json_message =json.dumps({'type': WRtype  ,'data' :{'deviceName' : deviceName, 'content' : content , 'size' : size , 'font' : font, 'color' : color , 'locate' : locate , 'speed' : speed , 'direction' : direction }})
            print(json_message)
            try:
                if soc_port in socketList:
                    socket_obj = socketList[soc_port]
                    socket_obj.sendall(json_message.encode('utf-8'))
                    print("Data sent successfully.")
                else:
                    print("Port number not found in socketList.")
            except Exception as ex:
                QMessageBox().warning(self, 'Warning(3)', str(ex))
                return 99
                            
        
        elif self.sd_tab.currentIndex() == 1:
            updateMediaDB(
                        self.sd_smilePlayTime.value(),
                        self.sd_smileFile.text(),
                        self.sd_sadPlayTime.value(),
                        self.sd_sadFile.text(),
                        self.sd_uuid.text()
                        )
            file_name_happy = self.sd_smileFile.text() # 전송할 파일 경로
            file_name_happy = os.path.basename(file_name_happy)    
            file_path_happy , file_extension_happy = os.path.splitext(file_name_happy)

            file_name_unhappy = self.sd_sadFile.text()
            file_name_unhappy = os.path.basename(file_name_unhappy)  
            file_path_unhappy , file_extension_unhappy = os.path.splitext(file_name_unhappy)

            PlayTime_happy = self.sd_smilePlayTime.value()
            PlayTime_unhappy = self.sd_sadPlayTime.value()
            
            json_message =json.dumps({'type': 'Media', 'data' :{'PlayTime_happy': PlayTime_happy, 'file_name_happy': file_name_happy, 'file_extension_happy': file_extension_happy, 'PlayTime_unhappy': PlayTime_unhappy, 'file_name_unhappy': file_name_unhappy, 'file_extension_unhappy': file_extension_unhappy}})
            
            print(json_message)
            try:
                if soc_port in socketList:
                    socket_obj = socketList[soc_port]
                    socket_obj.sendall(json_message.encode('utf-8'))
                    print("Data sent successfully.")
                else:
                    print("Port number not found in socketList.")  
            except Exception as ex:
                QMessageBox().warning(self, 'Warning(4)', str(ex))
                return 99

class PreviewThread(QThread):
    changeTextPreview = pyqtSignal(QGraphicsScene)

    def __init__(self, parent, txt, font, Red, Green, Blue, rotate, a, b, c, d, spd):
        self.txt = txt
        self.font = font
        self.Red = Red
        self.Green = Green
        self.Blue = Blue
        self.rotate = rotate
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.spd = spd

        super().__init__(parent)
        self.power = True

    def run(self):
        for i in range(self.rotate + len(self.txt)*40):
            pix = QPixmap(".\\ui\\previewBg.png")
            item = QGraphicsPixmapItem(pix.scaled(329, 459))
            scene = QGraphicsScene(self)
            t = QGraphicsTextItem(self.txt)

            scene.clear()
            scene.addItem(item)
            t.setFont(self.font)
            t.setDefaultTextColor(QColor(self.Red, self.Green, self.Blue))
            x = self.a + (self.c*i)
            y = self.b + (self.d*i)
            t.setPos(x, y)
            scene.addItem(t)
            self.changeTextPreview.emit(scene)
            time.sleep(self.spd)

    def stop(self):
        self.power = False
        self.quit()
        self.terminate()

# s쿼리
#############################################
def selectDB(uuid):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql = "SELECT * FROM setting WHERE s_uuid='" + uuid +"'"
    cursor.execute(sql)
    conn.commit()
    db_list = cursor.fetchall()
    conn.close()
    return db_list

def updateTxtDB(type, devicename, contents, size, font, color, locate, speed, direction, uuid):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql  = "UPDATE setting SET s_devicename = ?, s_"+ type +"_contents = ?, s_"+ type +"_size = ?, s_"+ type +"_font = ?, s_"+ type +"_color = ?, s_"+ type +"_locate = ?, s_"+ type +"_speed = ?, s_"+ type +"_direction = ? WHERE s_uuid = ?"
    param = (devicename, contents, size, font, color, locate, speed, direction, uuid)
    cursor.execute(sql, param)
    conn.commit()
    conn.close()

def updateMediaDB(smileplaytime, smilefile, sadplaytime, sadfile, uuid):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql  = "UPDATE setting SET s_smileplaytime = ?, s_smilefile = ?, s_sadplaytime = ?, s_sadfile = ? WHERE s_uuid = ?"
    param = (smileplaytime, smilefile, sadplaytime, sadfile, uuid)
    cursor.execute(sql, param)
    conn.commit()
    conn.close()
#############################################
# e쿼리

if __name__ == "__main__":
    app = QApplication(sys.argv)
    settingDetail = SettingDetail('0ca0086fc3053de3')
    settingDetail.show()
    app.exec_()