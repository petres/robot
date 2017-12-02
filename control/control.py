#!/usr/bin/env python
import sys
import serial
from PyQt5.QtWidgets import QDialog, QApplication

from gui.first import Ui_Robot

import time

Sliders = [{
    'name': 'Bottom',
    'output': 1,
}, {
    'name': 'Right',
    'output': 0,
}, {
    'name': 'Left',
    'output': 2,
}, {
    'name': 'Top',
    'output': 3,
}]

class ImageDialog(QDialog, Ui_Robot):

    def __init__(self):
        super(ImageDialog, self).__init__()
        self.ser = serial.Serial('/dev/ttyACM0', 2000000, timeout=1)

        self.setupUi(self)

        for i, s in enumerate(Sliders):
            slider = getattr(self, "verticalSlider_" + str(i + 1))
            label = getattr(self, "label_" + str(i + 1))
            label.setText(s['name'])
            slider._number = s['output']
            slider.valueChanged.connect(self.valueChanged)

    def valueChanged(self, value):
        #print('valueChanged')
        sender = self.sender()
        if self.ser.isOpen():
            self.ser.write(str(sender._number).encode('ascii') + b':' + str(value).encode('ascii') + b'\n')


app = QApplication(sys.argv)
window = ImageDialog()

window.show()

sys.exit(app.exec_())
