# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 14:33:37 2017

@author: lyb
"""
import tushare as ts
import tkinter as tk
import gdate as gd
import tkinter.scrolledtext as tkst


from os import path, getcwd
from dateu import get_date
from numpy import array
from datetime import datetime
from retrying import retry
from win32gui import SetForegroundWindow, GetForegroundWindow, FindWindow, FlashWindowEx

import win32con
import time
import _thread

# ******* Body Code *******
n = 0.0     # Time interval parameter
perc = 0.0  # Percent threshold parameter
lines = []  # Stock name list

taskbar = FindWindow("Shell_TrayWnd", None)

ttl = datetime.now()
ttl = str(ttl) + ' - ' + path.basename(path.normpath(getcwd()))


# ******* Subroutines *******
def chinese(oldstr, length):
    count = 0
    for s in oldstr:
        if ord(s) > 127:
            count += 1
    newstr = oldstr
    if length > count:
        newstr = '{0:{wd}}'.format(oldstr, wd=length - count)
    return newstr


def Flash():
    ID = FindWindow(None, ttl)
    FlashWindowEx(ID, win32con.FLASHW_STOP, 0, 0)
    cur_foreground = GetForegroundWindow()
    if ID == cur_foreground:
        SetForegroundWindow(taskbar)
    FlashWindowEx(ID, win32con.FLASHW_ALL |
                  win32con.FLASHW_TIMERNOFG, 0, 0)
    return

@retry
def ult_get_realtime_quotes(lines):
    return ts.get_realtime_quotes(lines)


def get_hist_vol(date, pt):
    'Get history volume'
    global lines
    vol_hist = [0 for i in range(len(lines))]
    for ir in range(len(lines)):
        dfy = ts.get_hist_data(lines[ir], start=date, end=date)
        if dfy.empty:
            txt = str(lines[ir]) + ' ' + date + ' 停牌'
            my_gui.update_disp(txt)
        else:
            vol_hist[ir] = dfy.iloc[0]['volume']
        if(pt == 1 and vol_hist[ir] > 0):
            txt = str(lines[ir]) + ' ' + date + \
                ' 日交易量为 ' + str(vol_hist[ir])
            my_gui.update_disp(txt)
    vol_hist = array(vol_hist)
    lines = array(lines)[vol_hist != 0].tolist()
    vol_hist = vol_hist[vol_hist != 0].tolist()
    return vol_hist


def get_real_vol(pt):
    'Get real-time volume'
    global lines
    dft = ult_get_realtime_quotes(lines)
    vol_real = dft['volume'].tolist()
    vol_real = [float(i) / 100 for i in vol_real]
    amt_real = dft['amount'].tolist()
    amt_real = [float(i) for i in amt_real]
    localtime = dft['time'].tolist()
    name = dft['name'].tolist()
    prc_real, prcc = get_price_change(dft)
    if(pt == 1):
        txt = today + ' ' + str(localtime) + ' 时成交量为 ' + str(vol_real)
        my_gui.update_disp(txt)
    return vol_real, amt_real, prc_real, localtime, name, prcc


def get_price_change(dft):
    'Get real-time price change wrt. the close price of yesterday'
    prc = dft['price'].tolist()
    prc = [float(i) for i in prc]
    prc_hist = dft['pre_close'].tolist()
    prc_hist = [float(i) for i in prc_hist]
    prc_change = [i for i in range(len(prc))]
    for ir in range(len(prc)):
        prc_change[ir] = (prc[ir] - prc_hist[ir]) / prc_hist[ir]
    return prc, prc_change


def cal_vol(vol_1, vol_2, vol_y, amnt_1, amnt_2, prc_1, prc_2,
            name, localtime, prcc, pt):
    'Compute real-time volume within a short period'
    global n
    global perc
    atxt = ''
    for ir in range(len(vol_1)):
        if(pt == 1):
            print(name[ir], localtime[ir], '起过去', str(n), '分钟内成交',
                  str(vol_2[ir] - vol_1[ir]))
        rt = (vol_2[ir] - vol_1[ir]) / vol_y[ir] * 100.
        at = amnt_2[ir] - amnt_1[ir]
        if prc_1[ir] > 0.:
            pt = (prc_2[ir] - prc_1[ir]) / prc_1[ir]
        else:
            pt = 0.
        if(rt > perc):
            atmp = chinese(str(name[ir]), 9) +\
                "{:<10}".format(str(localtime[ir])) +\
                "{:<9}".format(str(format(prcc[ir], '.2%'))) +\
                "{:<11}".format(str(format(pt, '.2%'))) +\
                "{:<8}".format(str(at)) +\
                ' || ' + str(n) + '分钟内成交量为昨日' +\
                "{:<8}".format(str(format(rt / 100., '.2%')))
            atxt = atxt + '\n' + atmp
            my_gui.update_disp(atmp)
            Flash()
    return


def trig_alert(mygui, pt):
    'Alert if the condition is satisfied'
    global yesterday
    global n
    global lines
    vol_y = get_hist_vol(yesterday, 0)
    my_gui.update_disp('************* 开始监控盘中实时交易量 *************')
    txt = chinese('股名', 9) + chinese('时间', 10) + chinese('涨幅', 9) +\
        chinese('瞬时涨幅', 11) + chinese('成交金额', 8)
    my_gui.update_disp(txt)
    vol_1, amt_1, prc_1, localtime, name, prcc = get_real_vol(pt)
    count = 0
    time.sleep(int(n * 60))
    atxt = ''
    while(count < 420 / n):
        vol_2, amt_2, prc_2, localtime, name, prcc = get_real_vol(0)
        vol_2 = [i + 2000 for i in vol_1]  # Only for test
        cal_vol(vol_1, vol_2, vol_y, amt_1, amt_2, prc_1, prc_2,
                name, localtime, prcc, pt)
        vol_1 = vol_2
        amt_1 = amt_2
        prc_1 = prc_2
        count = count + 1
        time.sleep(int(n * 60))
    my_gui.update_disp( '监控完成！')
    return


def tutest_procd(mygui):
    global yesterday
    global n
    global perc
    global lines
    try:
        n = float(my_gui.editArea1.get())
        perc = float(my_gui.editArea2.get())
        yesterday = my_gui.editArea3.get()
        datetime.strptime(yesterday, '%Y-%m-%d')
    except ValueError:
        my_gui.update_disp("参数不是正确！请重新输入！！!")
        return
    # Read Stock Codes
    with open("股票代码.txt") as f:
        lines = [r.split()[0] for r in f]
    my_gui.dispArea.configure(state='normal')
    my_gui.dispArea.delete('1.0', 'end')
    my_gui.update_disp(" 监控股票 " + str(lines))
    # Trigger Alert by Comparing Real Time Volumes
    _thread.start_new_thread(trig_alert, (mygui,0))

class MyGUI:
    global yesterday
    global ttl
    def __init__(self):
        self.master = master = tk.Tk()
        self.init_win()
        self.editArea1 = self.init_inp(0, 1, "周期分钟   -->", str(2))
        self.editArea2 = self.init_inp(1, 1, "百分阈值   -->", str(2))
        self.editArea3 = self.init_inp(2, 1, "上个交易日 -->", yesterday)
        self.btnBg = self.init_btn(0, 2, "开始")
        self.btnQt = self.init_btn(1, 2, "退出")
        self.init_disp()

        self.btnBg = tk.Button(self.frame, text="开始", command=lambda:tutest_procd(self))
        self.btnBg.grid(padx=40, row=0, column=2, columnspan=2, sticky='nsew')
        self.btnQt = tk.Button(self.frame, text="退出", command=master.destroy)
        self.btnQt.grid(padx=40, row=1, column=2, columnspan=2, sticky='nsew')

    def init_win(self):
        self.master.geometry('600x300+10+10')
        self.master.title(ttl)
        self.frame = tk.Frame(master=self.master)
        self.frame.grid(row=0, column=0, sticky='nsew')
        tk.Grid.rowconfigure(self.master, 0, weight=1)
        tk.Grid.columnconfigure(self.master, 0, weight=1)

    def init_btn(self, ro, co, txt):
        btn = tk.Button(master=self.frame, text=txt)
        btn.grid(padx=40, row=ro, column=co, columnspan=2, sticky='nsew')
        return btn

    def init_inp(self, ro, co, label, txt):
        tk.Label(master=self.frame, text=label).grid(
            padx=10, row=ro, column=co - 1, sticky='w')
        editArea = tk.Entry(master=self.frame, width=15)
        editArea.grid(padx=40, row=ro, column=co, sticky='w')
        editArea.insert(0, txt)
        return editArea

    def init_disp(self):
        self.dispArea = tkst.ScrolledText(
            master=self.frame, wrap=tk.WORD, width=60, height=10)
        self.dispArea.grid(padx=10, pady=10, row=3, column=0,
                           columnspan=4, rowspan=4, sticky='nsew')
        self.dispArea.bind("<1>", lambda event: self.dispArea.focus_set())
        self.update_disp('等待指示！')
        tk.Grid.rowconfigure(self.frame, 3, weight=1)
        tk.Grid.columnconfigure(self.frame, 0, weight=1)

    def update_disp(self, txt):
        self.dispArea.configure(state='normal')
        self.dispArea.insert('end', txt + '\n')
        self.dispArea.configure(state='disabled')
        self.dispArea.see('end')
        self.dispArea.update()

today, yesterday = get_date()
my_gui = MyGUI()
my_gui.master.mainloop()
