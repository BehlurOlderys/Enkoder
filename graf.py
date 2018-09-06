from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import serial
from math import sin, cos, atan2, pi;
data = ""
MAXPOINTS = 2000;
plik = open("log.txt", "w");
counter = 0;
mtime = 0;

class YourThreadName(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.arduino = serial.Serial("COM3", 115200, timeout=.5)

    def __del__(self):
        global plik
        plik.close()
        self.wait()

    def run(self):
        global data
        while True:
            dataRaw = self.arduino.readline()[:-2]
            if dataRaw:
                data = dataRaw
            else:
                print("timeout")

app = QtGui.QApplication([])


myPlot = pg.plot()
curveA = myPlot.plot(pen=pg.mkPen('r'))
dataA = [0,0,0,0,0,0,0,0,0,0]

curveB = myPlot.plot(pen=pg.mkPen('g'))
dataB = [0,0,0,0,0,0,0,0,0,0]

curveC = myPlot.plot(pen=pg.mkPen('b'))
dataC = [0,0,0,0,0,0,0,0,0,0]

curveD = myPlot.plot(pen=pg.mkPen('y'))
dataD = [0,0,0,0,0,0,0,0,0,0]

curveE = myPlot.plot(pen=pg.mkPen('w'))
dataE = [0,0,0,0,0,0,0,0,0,0]

myThread = YourThreadName()
myThread.start()

amplitudeA = 2000.0;
offsetA = 6000.0;
amplitudeB = 2000.0;
offsetB = 6000.0;
calcA = 0.0;
calcB = 0.0;
phi = 0.0;
lambdaOA = 0.1;
lambdaOB = 0.1;
lambdaUA = 0.1;
lambdaUB = 0.1;

def GetAngle(channelA, channelB):
    global offsetA, offsetB, amplitudeA, amplitudeB, calcA, calcB;
    bareA = (channelA - offsetA) / amplitudeA;
    bareB = (channelB - offsetB) / amplitudeB;
    phi = atan2(bareA, bareB);
    sinphi = sin(phi);
    cosphi = cos(phi);
    calcA = offsetA + amplitudeA * sinphi;
    calcB = offsetB + amplitudeB * cosphi;
    errorA = channelA - calcA;  
    errorB = channelB - calcB;
    offsetA += lambdaOA * errorA;
    offsetB += lambdaOB * errorB;
    amplitudeA += lambdaUA * errorA * sinphi;
    amplitudeB += lambdaUB * errorB * cosphi;
    return phi;
    
def AppendValueToDataAndPrint(value, data, curve):
    if len(data) > MAXPOINTS:
        data.pop(0)
    data.append(value)
    curve.setData(data)


lastTimestamp = 0


def updater():
    global data
    global plik
    global phi
    global counter
    global mtime
    global lastTimestamp

    stringData = data.decode("utf-8")
    enkoderTag = '[E]'
    if not enkoderTag in stringData:
        return

    stringData = stringData[len(enkoderTag):]

    #print(stringData)

    cspairs = dict(item.strip().split(':') for item in stringData.split(','))
    #print(cspairs)
    try:
        channelA = int(cspairs['A'])
        channelB = int(cspairs['B'])
        errorA = int(cspairs['C']) / 100
        errorB = int(cspairs['D']) / 100
        phi_100 = int(cspairs['F']) / 100
        timestamp = int(cspairs['T'])
    except KeyError as ke:
        print('Key error: %s' % str(ke))
        return

    timeDelta = timestamp - lastTimestamp
    lastTimestamp = timestamp
    if timeDelta == 0:
        return
    print('TIME DIFF: %s' % str(timeDelta))

    AppendValueToDataAndPrint(channelA, dataA, curveA)
    AppendValueToDataAndPrint(channelB, dataB, curveB)
    #AppendValueToDataAndPrint(errorA, dataC, curveC);
    #AppendValueToDataAndPrint(errorB, dataD, curveD);
    #AppendValueToDataAndPrint(360.0+360.0*phi, dataE, curveE);
"""
 if (counter > 1000):
        counter = 0
        print ('mtime = ' + str(mtime) + ', delta = ' + str((timeT - mtime)/1000) + 's, sps = '+str(1000000.0/(timeT - mtime))) # + SPS = ' + str(1000000/(mtime - timeT)))
        mtime = timeT
        
    counter +=1;
    
    #print ('T = ' + str(timeT) + ', A = ' + str(channelA) + ', B = ' + str(channelB))
    phi = GetAngle(channelA, channelB)/pi;
    
    #plik.write(str(channelA) + ":" + str(channelB) + ":" + str(supplyVdd) + "\n")
"""



timer = QtCore.QTimer()
timer.timeout.connect(updater)
timer.start(0)

if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()