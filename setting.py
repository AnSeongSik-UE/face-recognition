import sqlite3
import socket
import json
import threading
import sys
from datetime import datetime
from PyQt5.QtWidgets import QTableWidgetItem, QApplication, QMainWindow, QMessageBox
from PyQt5 import uic
from PyQt5.QtCore import QThread, QMutex, QThread, Qt
from PyQt5.QtNetwork import QNetworkInterface, QAbstractSocket
from PyQt5.QtGui import QFont
import setting_detail

sw_toggle = ''
socketList = {}
setting_ui = uic.loadUiType("./ui/setting.ui")[0]
class SettingWindow(QMainWindow, setting_ui):
    def __init__(self, mainWindow):
        super().__init__()
        self.setupUi(self)
        self.loadProcess()        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.mainWindow = mainWindow

        internal_ipv4 = self.get_internal_ipv4()
        self.lineEdit_IP.setText(internal_ipv4)
        self.lineEdit_port.setText('8765')
        self.clickConnect()        
        self.btn_delete_2.clicked.connect(self.disconnect_button_clicked)
        self.btn_setting.clicked.connect(self.clickSetting)
        self.sd_happyRate.valueChanged.connect(self.changeRate)
        self.sd_unhappyRate.valueChanged.connect(self.changeRate)

        self.label_connection_count.setText("0")  # 레이블 초기 값 설정
        

        self.label.setFont(QFont('굴림', 9))
        self.label_4.setFont(QFont('굴림', 9))
        self.label_5.setFont(QFont('굴림', 9))
        self.label_13.setFont(QFont('굴림', 9))
        self.label_14.setFont(QFont('굴림', 9))
        self.label_15.setFont(QFont('굴림', 9))
        self.label_16.setFont(QFont('굴림', 9))
        self.label_connection_count.setFont(QFont('굴림', 9))
        self.btn_execute.setFont(QFont('굴림', 9))
        self.btn_delete_2.setFont(QFont('굴림', 9))
        self.btn_setting.setFont(QFont('굴림', 9))
        self.lineEdit_IP.setFont(QFont('굴림', 9))
        self.lineEdit_port.setFont(QFont('굴림', 9))
        self.cf_table.setFont(QFont('굴림', 9))
        self.sd_happyRate.setFont(QFont('굴림', 9))
        self.sd_unhappyRate.setFont(QFont('굴림', 9))
        self.label_happy_count.setFont(QFont('굴림', 9))
        self.label_unhappy_count.setFont(QFont('굴림', 9))

    #얼굴인식 cnt값이 10만이상인경우 0으로 초기화
    def maxCheck(self, cnt):
        if cnt >= 100000:
            return 0
        else:
            return cnt

    # 얼굴인식 cnt
    def upCnt(self, status):
        if status == 'happy':
            cnt = int(self.label_happy_count.text()) + 1
            cnt = self.maxCheck(cnt)
            updateCnt('happy', cnt)
            self.label_happy_count.setText(str(cnt))
        elif status == 'unhappy':
            cnt = int(self.label_unhappy_count.text()) + 1
            cnt = self.maxCheck(cnt)
            updateCnt('unhappy', cnt)
            self.label_unhappy_count.setText(str(cnt))

    def closeEvent(self, event):
        event.ignore()
        self.toggle_True()
        self.showMinimized()

    # 데이터 불러오기
    def loadProcess(self):
        global row_count
        global tables_data
        
        self.cf_table.setSortingEnabled(False)
        ms_data = selectMainDB()
        self.sd_happyRate.setValue(ms_data[0][0])
        self.sd_unhappyRate.setValue(ms_data[0][1])
        self.label_happy_count.setText(str(ms_data[0][2]))
        self.label_unhappy_count.setText(str(ms_data[0][3]))
        
        tables_data = selectDB()
        row_count = len(tables_data) #row 행
        self.cf_table.setRowCount(row_count)

        count=0
        for i in tables_data:
            item_name = QTableWidgetItem(str(i[1]))
            self.cf_table.setItem(count, 0, item_name)
            item_name = QTableWidgetItem(str(i[2]))
            self.cf_table.setItem(count,1,item_name)
            item_name = QTableWidgetItem(str('-'))
            self.cf_table.setItem(count,2,item_name)
            item_name = QTableWidgetItem(str('-'))
            self.cf_table.setItem(count,3,item_name)
            item_name = QTableWidgetItem(str('-'))
            self.cf_table.setItem(count,4,item_name)
            item_name = QTableWidgetItem(str('-'))
            self.cf_table.setItem(count,5,item_name)
            count=count+1
        self.cf_table.setSortingEnabled(True)
        

    def showCamera(self):
        self.mainWindow.show()
        self.close()
    
    #웃음,슬픔 인식률 DB 업데이트
    def changeRate(self):
        happy_rate = self.sd_happyRate.value()
        unhappy_rate = self.sd_unhappyRate.value()
        self.mainWindow.face_recognizer.SMILE_SCORE = happy_rate #실시간 얼굴인식 인식률 변경
        self.mainWindow.face_recognizer.SAD_SCORE = unhappy_rate
        print(f'changeRate happy : {happy_rate}  unhappy : {unhappy_rate}')

        conn = sqlite3.connect('db.db')
        cursor = conn.cursor()
        sql  = "UPDATE main_setting SET ms_happy_rate = ?, ms_unhappy_rate = ?, ms_date = ?"
        param = (happy_rate, unhappy_rate, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        cursor.execute(sql, param)
        conn.commit()
        conn.close()        

    #[서버실행] 버튼
    def clickConnect(self):
        self.worker = Worker(self)
        self.worker.start()

    def get_internal_ipv4(self):
        interfaces = QNetworkInterface.allInterfaces()
        for interface in interfaces:
            if interface.flags() & QNetworkInterface.IsUp and not interface.flags() & QNetworkInterface.IsLoopBack:
                addresses = interface.addressEntries()
                for address in addresses:
                    if address.ip().protocol() == QAbstractSocket.IPv4Protocol:
                        return address.ip().toString()
        return ""

    def clickSetting(self):
        if hasattr(self, 'setting_Window') and self.setting_Window is not None:
            self.setting_Window.close()  # 열려 있는 창이 있다면 닫기

        selected_rows = self.cf_table.selectionModel().selectedRows()

        #선택된 row가 없을경우
        if len(selected_rows) <= 0:
            QMessageBox().warning(self, 'Warning', 'No client selected.')
            return False

        for row in selected_rows:
            states = self.cf_table.item(row.row(), 3).text()

            # 연결확인
            if states !='Connected':
                QMessageBox().warning(self, 'Warning', 'The selected client is in a disconnected state.')
            else:
                selected_row = self.cf_table.currentRow()  # 선택된 행 인덱스 가져오기
                if selected_row >= 0:
                    soc_port = self.cf_table.item(selected_row, 5)  # IP 주소 아이템 가져오기
                    soc_port = soc_port.text()
                
                self.setting_Window = setting_detail.SettingDetail(self.cf_table.item(row.row(), 1).text(),socketList,soc_port)
                self.toggle_False()
                self.setting_Window.exec_()
                item_name = QTableWidgetItem(str(self.setting_Window.changedName))
                self.cf_table.setItem(row.row(), 0, item_name)
                
    def disconnect_button_clicked(self):
        self.cf_table.setSortingEnabled(False)
        buttonReply = QMessageBox.warning(self, 'Warning', 'Do you want me to delete it?', QMessageBox.Yes, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            selected_rows = self.cf_table.selectionModel().selectedRows()
            #선택된 row가 없을경우
            if len(selected_rows) <= 0:
                QMessageBox().warning(self, 'Warning', 'No client selected.')
                return False
            
            selected_row = self.cf_table.currentRow()  # 선택된 행 인덱스 가져오기
            if selected_row >= 0:
                uuid = self.cf_table.item(selected_row, 1).text()

                if self.cf_table.item(selected_row, 3).text() == 'Connected':
                    soc_port = self.cf_table.item(selected_row, 5)  # IP 주소 아이템 가져오기
                    soc_port = soc_port.text()
                    self.cf_table.removeRow(selected_row)
                    self.connectrow_count()#접속된 기기 카운팅

                    socketList[soc_port].close()
                    del socketList[soc_port]
                    deleteDB(uuid)
                else: 
                    self.cf_table.removeRow(selected_row)
                    deleteDB(uuid)
        self.cf_table.setSortingEnabled(True)
            
    def f1(self, soc): # 클라이언트 소켓(soc)을 parameter로 사용
        while True:
            try:
                msg = soc.recv(1024).decode("utf8")
                soc_port = str(soc.getpeername()[1]) #원격포트찾기
                soc_ip = str(soc.getpeername()[0]) #ip찾기

                #msg값이 있을때만 동작 
                if msg != '':
                    cmd = json.loads(msg)

                    if cmd['type'] == 'info':
                        print(f"cmd['type'] : {cmd['type'] }")
                        self.add_table_item(cmd, soc_ip,  soc_port, "Connected")
                    
                    #클라이언트로부터 파일 수신 대기 신호 전달받을시
                    if cmd['type'] == 'receive_stanby':
                        print(f"cmd['type'] : {cmd['type'] }")
                        self.setting_Window.receiveStanby = False
                elif msg == '': 
                    print(datetime.now())
                    self.disconnect_table(soc_ip, soc_port, "Disconnected")
                    break
                    
            except Exception as ex:
                print('소켓문제에러' + str(ex))  
                print(f"soc_ip : {soc_ip}") 
                print(f"soc_port : {soc_port}") 
                self.disconnect_table(soc_ip, soc_port, "Disconnected")
                break

    def add_table_item(self, cmd, ip, soc_port, status):
        self.cf_table.setSortingEnabled(False)
        row_count = self.cf_table.rowCount()
        uuid = cmd['uuid']
        orientation = cmd['orientation']
        device_name = cmd['device_name']

        for row in range(self.cf_table.rowCount()):
            item = self.cf_table.item(row, 1)
           
            if self.cf_table.item(row, 1).text() == uuid: #이미 해당 기기가 있으면 추가하지 않음
                item = self.cf_table.item(row, 3)
                item.setData(Qt.DisplayRole, status)

                self.cf_table.setItem(row, 1, QTableWidgetItem(uuid))
                self.cf_table.setItem(row, 2, QTableWidgetItem(ip))
                self.cf_table.setItem(row, 3, QTableWidgetItem(status))
                self.cf_table.setItem(row, 4, QTableWidgetItem(orientation))
                self.cf_table.setItem(row, 5, QTableWidgetItem(str(soc_port))) #접속포트
                self.connectrow_count()#접속된 기기 카운팅

                self.cf_table.viewport().update()
                self.cf_table.setSortingEnabled(True)
                return
            
        self.cf_table.insertRow(row_count)
        self.cf_table.setItem(row_count, 0, QTableWidgetItem(device_name))
        self.cf_table.setItem(row_count, 1, QTableWidgetItem(uuid))
        self.cf_table.setItem(row_count, 2, QTableWidgetItem(ip))
        self.cf_table.setItem(row_count, 3, QTableWidgetItem(status))
        self.cf_table.setItem(row_count, 4, QTableWidgetItem(orientation))
        self.cf_table.setItem(row_count, 5, QTableWidgetItem(str(soc_port))) #접속포트
        self.connectrow_count() #접속된 기기 카운팅

        insertDB(device_name, uuid ) #행 추가하면 DB에 INSERT
        self.cf_table.setSortingEnabled(True)

    #접속된 기기 카운팅
    def connectrow_count(self):
        con_count = 0
        for row in range(self.cf_table.rowCount()):
            if self.cf_table.item(row, 3).text() == 'Connected':
                con_count += 1
        self.label_connection_count.setText(str(con_count))
        return con_count

   #[시작] 버튼
    def showNormal(self):
        if self.isMinimized():
            super().showNormal()

    def toggle_True(self):
        global sw_toggle
        sw_toggle = True

    def toggle_False(self):
        global sw_toggle
        sw_toggle = False

    def emtionStatus_sad(self,cmd):
        if sw_toggle != False :
            sockets_to_remove = []  # 소켓을 제거할 목록
            for port, socket in socketList.items():
                try:
                    if port in socketList:
                        soc = socketList[port]
                        cmdToStr = json.dumps(cmd, ensure_ascii=False)
                        soc.sendall(cmdToStr.encode(encoding='utf-8'))

                except Exception as ex:
                    print(f"소켓 통신 오류 발생: {ex}")
                    sockets_to_remove.append(port)  # 통신 오류가 발생한 소켓을 목록에 추가

            # 소켓을 제거할 목록을 기반으로 socketList에서 해당 소켓들을 제거
            for port in sockets_to_remove:
                del socketList[port]
        
    #해당 소켓을 통해 서버에게 명령을 보냄
    def sendCommand(self, cmd, soc):
        soc.sendall(cmd.encode(encoding='utf-8'))

    def findSocket(self, port):
        if port in socketList:
            return socketList[port]
        else:
            return False

    def disconnect_table(self, ip, soc_port, status):
        sockets_to_remove = []  # 소켓을 제거할 목록
        for row in range(self.cf_table.rowCount()):

            if self.cf_table.item(row, 5).text() == soc_port :
                print('disconnect_table')
                item = self.cf_table.item(row, 3)
                item.setData(Qt.DisplayRole, status)
                self.connectrow_count() #접속된 기기 카운팅

                self.cf_table.viewport().update()
                for port in sockets_to_remove:
                    del socketList[port]                   
                return
       
class Worker(QThread):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        parent.btn_execute.setDisabled(True)
        self.mutex = QMutex()
    
    def run(self):
        try:
            host = self.parent.lineEdit_IP.text()
            port = int(self.parent.lineEdit_port.text())
            serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSock.bind((host, port))
            serverSock.listen(0)
        except Exception as ex:
            print(f'worker server init error - {ex}')

        while True:
            try:
                connectionSock, addr = serverSock.accept()
                socketList[str(addr[1])] = connectionSock
                self.connectThread(connectionSock)
            except Exception as ex:
                print(f'worker socket error - {ex}')

    def connectThread(self, connectionSock,):
        self.mutex.lock()
        th = threading.Thread(target=self.parent.f1, args=(connectionSock,))  
        th.start()
        self.mutex.unlock()

def updateCnt(type, cnt):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql = "UPDATE main_setting SET ms_" + type + "_count = ?"
    param = (cnt,)
    cursor.execute(sql, param)
    conn.commit()
    conn.close()

def selectMainDB():
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql = "SELECT * FROM main_setting"
    cursor.execute(sql)
    conn.commit()
    db_list = cursor.fetchall()
    conn.close()
    return db_list

def selectDB():
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql = "SELECT * FROM setting"
    cursor.execute(sql)
    conn.commit()
    db_list = cursor.fetchall()
    conn.close()
    return db_list

def deleteDB(uuid):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor() 
    sql = "DELETE FROM setting WHERE s_uuid = ?"
    param = (uuid,)
    cursor.execute(sql, param)
    conn.commit()
    deleted_rows = cursor.rowcount
    conn.close()
    return deleted_rows

def insertDB(devicename, uuid):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    sql  = "INSERT INTO setting (s_devicename, s_uuid) VALUES (?, ?)"
    param = (devicename, uuid)
    cursor.execute(sql, param)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    settingWindow = SettingWindow()
    settingWindow.show()
    sys.exit(app.exec_())