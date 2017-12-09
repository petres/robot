#!/usr/bin/env python
import sys
import serial
from PyQt5.QtWidgets import QDialog, QApplication

from gui.first import Ui_Robot

import time
import math

#serialPort = '/dev/ttyACM0'
serialPort = None

Sliders = {
    'servo': {
        'gamma': {
            'name': 'Bottom',
            'output': 0,
            'offset': 90,
        },
        'beta': {
            'name': 'Right',
            'output':   1,
            'length':  80,
            'offset': 153,
        },
        'alpha': {
            'name': 'Left',
            'output':   2,
            'length':  77,
            'offset':  54,
        },
        'theta': {
            'name': 'Top',
            'output': 3
        }
    },
    'circle': {
        'gamma': {
        },
        'length': {
        },
        'height': {
        }
    },
    'cartesian': {
        'x': {
        },
        'y': {
        },
        'z': {
        }
    }
}

class NotReachableException(Exception):
    pass


class ControlDialog(QDialog, Ui_Robot):

    def __init__(self):
        super(ControlDialog, self).__init__()
        if serialPort is not None:
            self.ser = serial.Serial(serialPort, 2000000, timeout=1)

        self.setupUi(self)

        for t, sliders in Sliders.items():
            for s, info in sliders.items():
                info['type'] = t

                info['slider'] = getattr(self, 'slider_{}_{}'.format(t, s))
                info['label'] = getattr(self, 'label_{}_{}'.format(t, s))

                if 'name' not in info:
                    info['name'] = s.capitalize()
                info['label'].setText(info['name'])

                info['slider']._info = info
                info['slider'].valueChanged.connect(self.valueChanged)

        for s, info in Sliders['servo'].items():
            info['slider'].setValue(90)

    def convert(self, src, values):
        servos = Sliders['servo']

        def circleToServo(v):
            pos_length = math.hypot(v['length'], v['height'])

            if servos['alpha']['length'] + servos['beta']['length'] < pos_length:
                raise NotReachableException('Robot arm too short')

            if v['length'] == 0:
                raise NotReachableException('Not a valid exception') #TODO
            angle_rad = math.atan(v['height']/v['length'])

            t_alpha_rad = math.acos((servos['alpha']['length']**2 + pos_length**2 - servos['beta']['length']**2)/(2*servos['alpha']['length']*pos_length))
            t_beta_rad = math.acos((servos['alpha']['length']**2 - pos_length**2 + servos['beta']['length']**2)/(2*servos['alpha']['length']*servos['beta']['length']))

            alpha = 90 + servos['alpha']['offset'] - (math.degrees(angle_rad) + math.degrees(t_alpha_rad))
            beta = math.degrees(t_beta_rad) - (180 - (math.degrees(t_alpha_rad) + math.degrees(angle_rad))) + servos['beta']['offset']

            return {'alpha': alpha, 'beta': beta, 'gamma': v['gamma']}


        def servoToCircle(v):
            alpha = 90 + servos['alpha']['offset'] - v['alpha']
            beta = v['beta'] - servos['beta']['offset']

            length = servos['alpha']['length']*math.cos(math.radians(alpha)) + servos['beta']['length']*math.cos(math.radians(beta))
            height = servos['alpha']['length']*math.sin(math.radians(alpha)) + servos['beta']['length']*math.sin(math.radians(beta))

            return {'gamma': v['gamma'], 'length': length, 'height': height}


        def circleToCartesian(v):
            gamma = v['gamma'] - servos['gamma']['offset']

            return {'x': v['length']*math.cos(math.radians(gamma)), 'y': v['length']*math.sin(math.radians(gamma)), 'z': v['height']}


        def cartesianToCircle(v):
            length =math.hypot(v['x'], v['y'])
            if length == 0:
                # THAT SHOULD BE UNDEFINED
                gamma = 0
            else:
                gamma = math.degrees(math.atan2(v['y'], v['x']))

            return {'gamma': gamma + servos['gamma']['offset'], 'length': length, 'height': v['z']}


        if src == "servo":
            values['circle'] = servoToCircle(values['servo'])
            values['cartesian'] = circleToCartesian(values['circle'])

        elif src == "circle":
            values['servo'] = circleToServo(values['circle'])
            values['cartesian'] = circleToCartesian(values['circle'])

        elif src == "cartesian":
            values['circle'] =  cartesianToCircle(values['cartesian'])
            values['servo'] = circleToServo(values['circle'])

        print(values)

        for i, v in values['servo'].items():
            if v < 0 or v > 180:
                raise NotReachableException('Servo position not in valid range (0-180)')


    def valueChanged(self, value):
        s_info = self.sender()._info

        orig = s_info['type']
        orig_values = {}

        for s, info in Sliders[orig].items():
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
            return

        for dest in Sliders:
            if dest == s_info['type']:
                continue

            for s, info in Sliders[dest].items():
                if s in values[dest]:
                    info['slider'].blockSignals(True)
                    info['slider'].setValue(values[dest][s])
                    info['label'].setText('{}\n{}'.format(info['name'], round(values[dest][s])))
                    info['slider'].blockSignals(False)


        if serialPort is not None and self.ser.isOpen():
            for k, v in values['servo'].items():
                self.ser.write(str(Sliders['servo'][k]['output']).encode('ascii') + b':' + str(v).encode('ascii') + b'\n')




app = QApplication(sys.argv)
window = ControlDialog()

window.show()

sys.exit(app.exec_())
