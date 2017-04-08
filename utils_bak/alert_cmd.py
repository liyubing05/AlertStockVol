# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 14:33:37 2017

@author: lyb
"""
import tkinter as tk
import datetime as dtt
import numpy as np
import time
import tushare as ts
import win32gui
import win32con
import _thread
from os import system

# Import smtplib for the actual sending function and  the email modules
# import smtplib
# from email.mime.text import MIMEText

global n
global perc

ttl = dtt.datetime.now()
ttl = str(ttl)
system("title " + ttl)
ID = win32gui.FindWindow(None, ttl)

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
    taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    win32gui.SetForegroundWindow(taskbar)
    win32gui.FlashWindowEx(ID, win32con.FLASHW_ALL |
                           win32con.FLASHW_TIMERNOFG, 0, 0)
    #win32gui.FlashWindowEx(ID, win32con.FLASHW_ALL, 500, 500)


def StopFlash():
    win32gui.FlashWindowEx(ID, win32con.FLASHW_STOP, 0, 0)


def ini_win():
    win = tk.Tk()
    win.title(ttl + "停止闪烁")
    win.geometry("250x150+30+30")
    bstop = tk.Button(master=win, text=ttl + "\n停止闪烁",
                      command=lambda: StopFlash())
    bstop.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side='top')
    win.mainloop()


def read_param(strng):
    'Read input parameters: codes of stock'
    val = input(strng) or str(2)
    fval = float(val)
    return val, fval


def get_date():
    'Get the date of today and yesterday'
    today = dtt.date.today()
    dayOfWeek = dtt.date.today().weekday()
    oneday = dtt.timedelta(days=0)
    if(dayOfWeek == 0):
        oneday = dtt.timedelta(days=3)
    yesterday = today - oneday
    today = str(today)
    yesterday = str(yesterday)
    return today, yesterday


def get_hist_vol(lines, date, pt):
    'Get history volume'
    vol_hist = [0 for i in range(len(lines))]
    for ir in range(len(lines)):
        dfy = ts.get_hist_data(lines[ir], start=date, end=date)
        if dfy.empty:
            print(lines[ir], yesterday, '停牌')
        else:
            vol_hist[ir] = dfy.iloc[0]['volume']
        if(pt == 1 and vol_hist[ir] > 0):
            print(lines[ir], yesterday, '日交易量为', str(vol_hist[ir]))
    vol_hist = np.array(vol_hist)
    lines = np.array(lines)[vol_hist != 0].tolist()
    vol_hist = vol_hist[vol_hist != 0].tolist()
    return vol_hist, lines


def get_real_vol(lines, pt):
    'Get real-time volume'
    dft = ts.get_realtime_quotes(lines)
    vol_real = dft['volume'].tolist()
    vol_real = [float(i) / 100 for i in vol_real]
    amt_real = dft['amount'].tolist()
    amt_real = [float(i) for i in amt_real]
    localtime = dft['time'].tolist()
    name = dft['name'].tolist()
    prc_real, prcc = get_price_change(dft)
    if(pt == 1):
        print(today, localtime, '时成交量为', str(vol_real))
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
    atxt = ''
    for ir in range(len(vol_1)):
        if(pt == 1):
            print(name[ir], localtime[ir], '起过去', str(n), '分钟内成交',
                  str(vol_2[ir] - vol_1[ir]))
        rt = (vol_2[ir] - vol_1[ir]) / vol_y[ir] * 100.
        at = amnt_2[ir] - amnt_1[ir]
        pt = (prc_2[ir] - prc_1[ir]) / prc_1[ir]
        if(rt > perc):
            atmp = chinese(str(name[ir]), 9) + "{:<10}".format(str(localtime[ir])) +\
                "{:<9}".format(str(format(prcc[ir], '.2%'))) +\
                "{:<11}".format(str(format(pt,'.2%'))) +\
                "{:<8}".format(str(at)) +\
                ' || ' + str(n) + '分钟内成交量为昨日' +\
                "{:<8}".format(str(format(rt / 100., '.2%')))
            print(atmp)
            atxt = atxt + '\n' + atmp
            _thread.start_new_thread(Flash, ())
    return


def trig_alert(lines, vol_y, pt):
    'Alert if the condition is satisfied'
    print('******** 开始监控盘中实时交易量 ********')
    txt = chinese('股名', 9) + chinese('时间', 10) + chinese('涨幅', 9) +\
          chinese('瞬时涨幅', 11) + chinese('成交金额', 8)
    print(txt)
    vol_1, amt_1, prc_1, localtime, name, prcc = get_real_vol(lines, pt)
    count = 0
    time.sleep(n * 60)
    atxt = ''
    while(count < 360 / n):
        vol_2, amt_2, prc_2, localtime, name, prcc = get_real_vol(lines, 0)
        vol_2 = [i + 2000 for i in vol_1]  # Only for test
        cal_vol(vol_1, vol_2, vol_y, amt_1, amt_2, prc_1, prc_2,
                name, localtime, prcc, pt)
        vol_1 = vol_2
        amt_1 = amt_2
        prc_1 = prc_2
        count = count + 1
        time.sleep(n * 60)
    return


# ******* Body Code *******

# Read Parameters
# _thread.start_new_thread(ini_win, ())

m, n = read_param('周期是多少分钟（默认2）？-->')
p, perc = read_param('百分阈值是多少（默认2）？-->')

# Read Stock Codes
with open("股票代码.txt") as f:
    lines = [r.split()[0] for r in f]
print("监控股票", lines)

# Get Date
today, yesterday = get_date()

# Download Volume of Yesterday
vol_y, lines = get_hist_vol(lines, yesterday, 0)

# Trigger Alert by Comparing Real Time Volumes
trig_alert(lines, vol_y, 0)

input('按下回车键关闭')
