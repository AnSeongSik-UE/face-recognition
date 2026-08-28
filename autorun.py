import subprocess
import time
import win32api
import schedule
from tendo import singleton

def job():
    try:
        path = '.\\SIM_Mobile_Communication.exe'                # 실행파일명 변경필요
        subprocess.run(path, shell=False)
    except:
        win32api.MessageBox(0, "Should be run in the same folder as 'SIM_Mobile_Communication.exe'.", "Error", 16)

if __name__ == '__main__':
    try:
        me = singleton.SingleInstance()
        job()
        # schedule.every(5).seconds.do(job)     # 재실행 주기
        schedule.every(1).minutes.do(job)
        while True:
            schedule.run_pending()
            time.sleep(1)
    except:
        win32api.MessageBox(0, "'autorun.exe' is already running.", "Error", 16)