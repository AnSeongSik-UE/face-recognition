from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
main_package = ['sqlite3', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'os', 'sys', 'time', 'numpy', 'win32api', 'win32.lib.win32con', 'cv2', 'mediapipe', 'mediapipe.tasks', 'pygame']

setting_package = ['sqlite3', 'socket', 'json', 'threading', 'sys', 'datetime', 'PyQt5.QtWidgets', 'PyQt5.uic', 'PyQt5.QtCore', 'PyQt5.QtNetwork', 'PyQt5.QtGui']

setting_detail_package = ['sqlite3', 'sys', 'time', 'base64', 'json', 'os', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.uic', 'PyQt5.QtGui', 'PyQt5.QtMultimedia']

build_options = {'packages': list(set(main_package + setting_package + setting_detail_package)), 'excludes': []}

import sys
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    #Executable(script="main.py", base=base, icon="./images/logo.ico", target_name="SIM_Mobile_Communication.exe") #콘솔창X
    Executable(script="main.py", icon="./images/logo.ico", target_name="SIM_Mobile_Communication.exe") #콘솔창O
]

setup(name='SIM_Mobile_Communication',
      version = '2.9',
      description = 'SIM_Mobile_Communication',
      options = {'build_exe': build_options},
      executables = executables)