#!/usr/bin/env python
import sys
import serial
from PyQt5.QtWidgets import QDialog, QApplication

from gui.control import Ui_Robot

import time
import math

import configparser

config = configparser.ConfigParser()
config.read('config.ini')

Sliders = {
    'servo': ['gamma', 'beta', 'alpha', 'theta'],
    'circle': ['gamma', 'r', 'z'],
    'cartesian': ['x', 'y', 'z'],
}

class NotReachableException(Exception):
    pass


class ControlDialog(QDialog, Ui_Robot):
    _sliders = {}

    def __init__(self):
        super(ControlDialog, self).__init__()
        self.setupUi(self)

        if config.getboolean('Serial', 'enabled'):
            self.ser = serial.Serial(config.get('Serial', 'port'), config.getint('Serial', 'baudrate'), timeout=1)
            self.showStatus('No serial connection.', 'success')
        else:
            self.showStatus('No serial connection.')


        for t, sliders in Sliders.items():
            self._sliders[t] = {}
            for s in sliders:
                info = {}
                info['type'] = t
                info['min'] = config.getint(s, 'min')
                info['max'] = config.getint(s, 'max')

                info['slider'] = getattr(self, 'slider_{}_{}'.format(t, s))
                info['label'] = getattr(self, 'label_{}_{}'.format(t, s))

                info['slider'].setMinimum(info['min'])
                info['slider'].setMaximum(info['max'])

                info['name'] = s.capitalize()
                info['label'].setText(info['name'])

                info['slider']._info = info
                info['slider'].valueChanged.connect(self.valueChanged)

                self._sliders[t][s] = info

        for s, info in self._sliders['servo'].items():
            info['slider'].setValue(90)


    def showStatus(self, status, type = 'notice'):
        self.statusLabel.setText(status)
        typeTocolor = {'notice': 'black', 'error': 'red', 'success': 'green'}
        self.statusLabel.setStyleSheet('color: {}'.format(typeTocolor[type]))


    def convert(self, src, values):
        alphaLength = config.getint('alpha', 'length')
        betaLength = config.getint('beta', 'length')

        alphaOffset = config.getint('alpha', 'offset')
        betaOffset = config.getint('beta', 'offset')
        gammaOffset = config.getint('gamma', 'offset')

        def circleToServo(v):
            pos_length = math.hypot(v['r'], v['z'])

            if alphaLength + betaLength < pos_length:
                raise NotReachableException('Robot arm too short')

            if v['r'] == 0:
                raise NotReachableException('Not a valid exception') #TODO
            angle_rad = math.atan(v['z']/v['r'])

            t_alpha_rad = math.acos((alphaLength**2 + pos_length**2 - betaLength**2)/(2*alphaLength*pos_length))
            t_beta_rad = math.acos((alphaLength**2 - pos_length**2 + betaLength**2)/(2*alphaLength*betaLength))

            alpha = 90 + alphaOffset - (math.degrees(angle_rad) + math.degrees(t_alpha_rad))
            beta = math.degrees(t_beta_rad) - (180 - (math.degrees(t_alpha_rad) + math.degrees(angle_rad))) + betaOffset

            return {'alpha': round(alpha), 'beta': round(beta), 'gamma': round(v['gamma'])}


        def servoToCircle(v):
            alpha = 90 + alphaOffset - v['alpha']
            beta = v['beta'] - betaOffset

            r = alphaLength*math.cos(math.radians(alpha)) + betaLength*math.cos(math.radians(beta))
            z = alphaLength*math.sin(math.radians(alpha)) + betaLength*math.sin(math.radians(beta))

            return {'gamma': v['gamma'], 'r': r, 'z': z}


        def circleToCartesian(v):
            gamma = v['gamma'] - gammaOffset

            return {'x': v['r']*math.cos(math.radians(gamma)), 'y': v['r']*math.sin(math.radians(gamma)), 'z': v['z']}


        def cartesianToCircle(v):
            r = math.hypot(v['x'], v['y'])
            if r == 0:
                # THAT SHOULD BE UNDEFINED
                gamma = 0
            else:
                gamma = math.degrees(math.atan2(v['y'], v['x']))

            return {'gamma': gamma + gammaOffset, 'r': r, 'z': v['z']}


        if src == "servo":
            values['circle'] = servoToCircle(values['servo'])
            values['cartesian'] = circleToCartesian(values['circle'])

        elif src == "circle":
            values['servo'] = circleToServo(values['circle'])
            values['cartesian'] = circleToCartesian(values['circle'])

        elif src == "cartesian":
            values['circle'] =  cartesianToCircle(values['cartesian'])
            values['servo'] = circleToServo(values['circle'])

        for i, v in values['servo'].items():
            if v < 0 or v > 180:
                raise NotReachableException('Out of range. Servo {} has value {}.'.format(i, v))


    def valueChanged(self, value):
        s_info = self.sender()._info

        orig = s_info['type']
        orig_values = {}

        for s, info in self._sliders[orig].items():
            v = info['slider'].value()
            info['label'].setText('{}\n{}'.format(info['name'], round(v)))
            orig_values[s] = v

        values = {}
        values[orig] = orig_values
        try:
            self.convert(s_info['type'], values)
        except NotReachableException as e:
            print('Not Reachable')
            print(e)
            self.showStatus(str(e), 'error')
            return

        for dest in self._sliders:
            if dest == s_info['type']:
                continue

            for s, info in self._sliders[dest].items():
                if s in values[dest]:
                    info['slider'].blockSignals(True)
                    info['slider'].setValue(values[dest][s])
                    info['label'].setText('{}\n{}'.format(info['name'], round(values[dest][s])))
                    info['slider'].blockSignals(False)


        message = " ".join(["{}:{}".format(config.getint(k, 'output'), v) for k, v in values['servo'].items()])
        self.messageEdit.setText(message)
        if config.getboolean('Serial', 'enabled') and self.ser.isOpen():
            message += "\n"
            self.ser.write(message.encode('ascii'))

        self.showStatus('Sent!', 'success')


app = QApplication(sys.argv)
window = ControlDialog()

window.show()

sys.exit(app.exec_())
