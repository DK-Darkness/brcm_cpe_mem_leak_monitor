import telnetlib
import time
import sys
import re
import yaml

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtGui, QtWidgets
from Ui_mem_leak_monitor import *

with open('config.yaml','r',encoding='utf-8') as f:
    config = f.read()
    config = yaml.load(config,Loader=yaml.FullLoader)

HOST_IP = config['HOST_IP']
USERNAME = config['USERNAME']
PASSWORD = config['PASSWORD']

tn = telnetlib.Telnet(HOST_IP, port=23)

start_time = int(time.time())

data_dict = {
    "cur_mem":0,
    "total_mem_leak":0,
    "prv_mem_1":0,
    "prv_mem_12":0,
    "prv_mem_24":0,
    "leak_1":0,
    "leak_12":0,
    "leak_24":0
}

def Login():
    try:
        tn.open(HOST_IP, port=23)
    except:
        print('{}网络连接失败'.format(HOST_IP))
    tn.read_until(b'Login: ', timeout=10)
    tn.write(USERNAME.encode('ascii') + b'\n')
    tn.read_until(b'Password: ', timeout=10)
    tn.write(PASSWORD.encode('ascii') + b'\n')
    time.sleep(2)
    command_result = tn.read_very_eager().decode('ascii')
    if 'Login incorrect' not in command_result:
        print('{}登录成功'.format(HOST_IP))
    else:
        print('{}登录失败，用户名或密码错误'.format(HOST_IP))

class BackendThread(QtCore.QObject):
    update_date = QtCore.pyqtSignal(dict)
    
    def run(self):
        temp = tn.read_very_eager().decode('ascii')
        tn.write('meminfo'.encode('ascii') + b'\n')
        time.sleep(1)
        temp = tn.read_very_eager().decode('ascii')
        parttern = re.compile('Shared Memory free             : (\d+)KB')
        prv_mem = int(parttern.findall(temp)[0])
        data_dict['prv_mem_1'] = prv_mem
        data_dict['prv_mem_12'] = prv_mem
        data_dict['prv_mem_24'] = prv_mem
        while True:
            global start_time
            temp = tn.read_very_eager().decode('ascii')
            tn.write('meminfo'.encode('ascii') + b'\n')
            time.sleep(1)
            temp = tn.read_very_eager().decode('ascii')
            parttern = re.compile('Shared Memory free             : (\d+)KB')
            current_mem = int(parttern.findall(temp)[0])
            data_dict["cur_mem"] = current_mem
            data_dict["total_mem_leak"] = prv_mem - current_mem
            cur_time = int(time.time())
            if (cur_time - start_time)/3600 == 1:
                data_dict["leak_1"] = data_dict["prv_mem_1"] - current_mem
                data_dict["prv_mem_1"] = current_mem
            elif (cur_time - start_time)/43200 == 1:
                data_dict["leak_12"] = data_dict["prv_mem_12"] - current_mem
                data_dict["prv_mem_12"] = current_mem
            elif (cur_time - start_time)/86400 == 1:
                data_dict["leak_24"] = data_dict["prv_mem_24"] - current_mem
                data_dict["prv_mem_24"] = current_mem
                start_time = cur_time
            self.update_date.emit(data_dict)

class MyWindow(QMainWindow, Ui_mainWindow):
    def __init__(self, parent=None):
        super(MyWindow, self).__init__(parent)
        self.setupUi(self)

        self.initUI()
    
    def initUI(self):
        # 创建线程
        self.backend = BackendThread()
        # 连接信号
        self.backend.update_date.connect(self.update_info)
        self.thread = QtCore.QThread()
        self.backend.moveToThread(self.thread)
        # 开始线程
        self.thread.started.connect(self.backend.run)
        self.thread.start()

    def update_info(self,data_dict):
        self.cur_mem_v.setText(str(data_dict["cur_mem"])+'KB')
        self.prv_mem_1_v.setText(str(data_dict["prv_mem_1"])+'KB')
        self.leak_1_v.setText(str(data_dict["leak_1"])+'KB')
        self.prv_mem_12_v.setText(str(data_dict["prv_mem_12"])+'KB')
        self.leak_12_v.setText(str(data_dict["leak_12"])+'KB')
        self.prv_mem_24_v.setText(str(data_dict["prv_mem_24"])+'KB')
        self.leak_24_v.setText(str(data_dict["leak_24"])+'KB')
        self.total_mem_leak_v.setText(str(data_dict["total_mem_leak"])+'KB')

if __name__ == '__main__':
    Login()
    app = QApplication(sys.argv)
    myWin = MyWindow()
    myWin.show()
    sys.exit(app.exec_())