import sys
sys.path.append('C:/Python37/Lib/site-packages')

from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import random
from pyOpenBCI import OpenBCICyton
import threading
import time
import numpy as np
from scipy import signal
import random

import numpy as np
from PIL import Image

img = Image.open('heart_1.png').convert('RGBA')
arr = np.array(img)

img2 = Image.open('heart_2.png').convert('RGBA')
arr2 = np.array(img2)


SCALE_FACTOR = (4500000)/24/(2**23-1) #From the pyOpenBCI repo
colors = 'rgbycmwr'

app = QtGui.QApplication([])
win = pg.GraphicsWindow(title='Python OpenBCI GUI')
# title_graph = win.addPlot(row=0, col=0, colspan=4,title='Python OpenBCI GUI')
ts_plots = win.addPlot(row=0, col=0, colspan=4, title='Channel %d' % 1, labels={'left': 'uV'})
fft_plot = win.addPlot(row=2, col=0, rowspan=2, colspan=2, title='Filtered Plot', labels={'left': 'uV', 'bottom': 'Hz'})
fft_plot.setLimits(xMin=1,xMax=125, yMin=0, yMax=1e7)
ss_plot = win.addPlot(row=4, col=0, rowspan=2, colspan=2, title='signal',labels={'left':'Is beat'})


heart_im = win.addViewBox(lockAspect=True)
imv = pg.ImageItem()

heart_im.addItem(imv)
imv.setImage(arr)
data= [0]


def save_data(sample):
    global data
    data.append(sample.channels_data[0]*SCALE_FACTOR)

def updater():
    global data, plots, colors
    fs = 250 #Hz
    disp_sec = 3 #Seconds to display

    t_data = np.array(data[-(fs*disp_sec + 100):]).T #transpose data

    #Notch Filter at 60 Hz
    def notch_filter(val, data, fs=250, b=5):
        notch_freq_Hz = np.array([float(val)])
        for freq_Hz in np.nditer(notch_freq_Hz):
            bp_stop_Hz = freq_Hz + 3.0 * np.array([-1, 1])
            b, a = signal.butter(b, bp_stop_Hz / (fs / 2.0), 'bandstop')
            fin = data = signal.lfilter(b, a, data)
        return fin


    def bandpass(start, stop, data, fs = 250):
        bp_Hz = np.array([start, stop])
        b, a = signal.butter(1, bp_Hz / (fs / 2.0), btype='bandpass')
        return signal.lfilter(b, a, data, axis=0)

    nf_data = np.array(notch_filter(60, t_data, b = 10))
    nf_data = np.array(notch_filter(50, nf_data, b = 10))
    bp_nf_data = np.array(bandpass(2, 50, nf_data))

    ts_plots.clear()
    ts_plots.plot(pen='r').setData(bp_nf_data[100:])

    #fft of data
    fft_plot.clear()

    sp = np.absolute(np.fft.fft(bp_nf_data))
    freq = np.fft.fftfreq(bp_nf_data.shape[-1], 1.0/fs)
    fft_plot.plot(pen='y').setData(freq, sp)

    one_beat = nf_data[100:300]
    filt = one_beat[::-1]

    ss_plot.clear()
    new_arr = bp_nf_data >  np.average(bp_nf_data) + np.std(bp_nf_data)
    ss_plot.plot(pen='g').setData(new_arr[100:]*1)



    if sum(new_arr[-100:]*1):
        imv.setImage(arr2)
    else:
        imv.setImage(arr)



def start_board():
    board = OpenBCICyton(port='COM5', daisy=False)
    board.start_stream(save_data)

if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        x = threading.Thread(target=start_board)
        x.daemon = True
        x.start()

        timer = QtCore.QTimer()
        timer.timeout.connect(updater)
        timer.start(0)


        QtGui.QApplication.instance().exec_()
