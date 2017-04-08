# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 14:33:37 2017

@author: lyb
"""
import datetime as dtt
import tushare as ts
import tkinter as tk
import tkinter.scrolledtext as tkst
from os import path, getcwd
from numpy import array
from pandas import read_csv
from retrying import retry
from win32gui import FindWindow, GetForegroundWindow, SetForegroundWindow, FlashWindowEx
import win32con
import time
import _thread


# ******* Body Code *******
n = 0.0     # Time interval parameter
perc = 0.0  # Percent threshold parameter
lines = []  # Stock name list

taskbar = FindWindow("Shell_TrayWnd", None)

ttl = dtt.datetime.now()
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
    cur_foreground = GetForegroundWindow()
    ID = FindWindow(None, ttl)
    if ID == cur_foreground:
        SetForegroundWindow(taskbar)
    FlashWindowEx(ID, win32con.FLASHW_ALL |
                  win32con.FLASHW_TIMERNOFG, 0, 0)
    #FlashWindowEx(ID, win32con.FLASHW_ALL, 500, 500)
    return


def StopFlash():
    ID = FindWindow(None, ttl)
    FlashWindowEx(ID, win32con.FLASHW_STOP, 0, 0)


def get_date():
    'Get the date of today and yesterday'
    tday = get_today()
    yday = last_tddate(tday)
    while is_holiday(str(yday)):
        yday = last_tddate(yday)
    return str(tday), str(yday)


def get_today():
    day = dtt.datetime.today().date()
    return day


def day_last_week(date, days=-7):
    lasty = date + dtt.timedelta(days)
    return lasty


def trade_cal():
    '''
            交易日历
    isOpen=1是交易日，isOpen=0为休市
    '''
    df = read_csv(ts.stock.cons.ALL_CAL_FILE)
    return df


def is_holiday(date):
    '''
            判断是否为交易日，返回True or False
    '''
    df = trade_cal()
    holiday = df[df.isOpen == 0]['calendarDate'].values
    if isinstance(date, str):
        tday = dtt.datetime.strptime(date, '%Y-%m-%d')

    if tday.isoweekday() in [6, 7] or date in holiday:
        return True
    else:
        return False


def last_tddate(tday):
    t = int(tday.strftime("%w"))
    if t == 0:
        return day_last_week(tday, -2)
    else:
        return day_last_week(tday, -1)


@retry
def ult_get_realtime_quotes(lines):
    return ts.get_realtime_quotes(lines)


def get_hist_vol(dpArea, date, pt):
    'Get history volume'
    global lines
    vol_hist = [0 for i in range(len(lines))]
    for ir in range(len(lines)):
        dfy = ts.get_hist_data(lines[ir], start=date, end=date)
        if dfy.empty:
            txt = str(lines[ir]) + ' ' + date + ' 停牌'
            update_disp(dpArea, txt)
        else:
            vol_hist[ir] = dfy.iloc[0]['volume']
        if(pt == 1 and vol_hist[ir] > 0):
            txt = str(lines[ir]) + ' ' + date + \
                ' 日交易量为 ' + str(vol_hist[ir])
            update_disp(dpArea, txt)
    vol_hist = array(vol_hist)
    lines = array(lines)[vol_hist != 0].tolist()
    vol_hist = vol_hist[vol_hist != 0].tolist()
    return vol_hist


def get_real_vol(dpArea, pt):
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
        update_disp(dpArea, txt)
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


def cal_vol(dpArea, vol_1, vol_2, vol_y, amnt_1, amnt_2, prc_1, prc_2,
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
            update_disp(dpArea, atmp)
            StopFlash()
            Flash()
            #_thread.start_new_thread(Flash, ())
    return


def trig_alert(dpArea, pt):
    'Alert if the condition is satisfied'
    global yesterday
    global n
    global lines
    vol_y = get_hist_vol(dpArea, yesterday, 0)
    update_disp(dpArea, '************* 开始监控盘中实时交易量 *************')
    txt = chinese('股名', 9) + chinese('时间', 10) + chinese('涨幅', 9) +\
        chinese('瞬时涨幅', 11) + chinese('成交金额', 8)
    update_disp(dpArea, txt)
    vol_1, amt_1, prc_1, localtime, name, prcc = get_real_vol(
        dpArea, pt)
    count = 0
    time.sleep(int(n * 60))
    atxt = ''
    while(count < 420 / n):
        vol_2, amt_2, prc_2, localtime, name, prcc = get_real_vol(
            dpArea, 0)
        # vol_2 = [i + 2000 for i in vol_1]  # Only for test
        cal_vol(dpArea, vol_1, vol_2, vol_y, amt_1, amt_2, prc_1, prc_2,
                name, localtime, prcc, pt)
        vol_1 = vol_2
        amt_1 = amt_2
        prc_1 = prc_2
        count = count + 1
        time.sleep(int(n * 60))
    update_disp(dpArea, '监控完成！')
    return


def tutest_procd(editArea1, editArea2, editArea3, dispArea):
    global yesterday
    global n
    global perc
    global lines
    try:
        n = float(editArea1.get())
        perc = float(editArea2.get())
        yesterday = editArea3.get()
        dtt.datetime.strptime(yesterday, '%Y-%m-%d')
    except ValueError:
        update_disp(dispArea, "参数不是正确！请重新输入！！!")
        return
    # Read Stock Codes
    with open("股票代码.txt") as f:
        lines = [r.split()[0] for r in f]
    dispArea.configure(state='normal')
    dispArea.delete('1.0', 'end')
    update_disp(dispArea, " 监控股票 " + str(lines))
    # Trigger Alert by Comparing Real Time Volumes
    _thread.start_new_thread(trig_alert, (dispArea, 0))


def init_win():
    win = tk.Tk()
    win.geometry('600x300+10+10')
    frame1 = tk.Frame(
        master=win
    )
    # frame1.pack(fill='both', expand='yes')
    tk.Grid.rowconfigure(win, 0, weight=1)
    tk.Grid.columnconfigure(win, 0, weight=1)
    frame1.grid(row=0, column=0, sticky='nsew')
    return win, frame1


def init_inp(frame, ro, co, txt):
    editArea = tk.Entry(
        master=frame,
        width=10
    )
    # editArea.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side='top')
    editArea.grid(padx=40, row=ro, column=co, sticky='w')
    tk.Label(master=frame, text=txt).grid(
        padx=10, row=ro, column=co - 1, sticky='w')
    return editArea


def init_disp(frame):
    dispArea = tkst.ScrolledText(
        master=frame,
        wrap=tk.WORD,
        width=60,
        height=10
    )
    # dispArea.pack(padx=10, pady=10, fill=tk.BOTH, expand=True, side='top')
    dispArea.grid(padx=10, pady=10, row=3, column=0,
                  columnspan=4, rowspan=4, sticky='nsew')
    tk.Grid.rowconfigure(frame, 3, weight=1)
    tk.Grid.columnconfigure(frame, 0, weight=1)
    dispArea.bind("<1>", lambda event: dispArea.focus_set())
    update_disp(dispArea, '等待指示！')
    return dispArea


def update_disp(dispArea, txt):
    dispArea.configure(state='normal')
    dispArea.insert('end', txt + '\n')
    dispArea.configure(state='disabled')
    dispArea.see('end')
    dispArea.update()


def init_tk():
    global yesterday
    root, frame = init_win()
    root.wm_title(ttl)
    editArea1 = init_inp(frame, 0, 1, "周期是多少分钟（默认2）？-->")
    editArea2 = init_inp(frame, 1, 1, "百分阈值是多少（默认2）？-->")
    editArea3 = init_inp(frame, 2, 1, "上个交易日日期（供核对） -->")
    dispArea = init_disp(frame)
    editArea1.insert(0, str(2))
    editArea2.insert(0, str(2))
    editArea3.insert(0, yesterday)
    bstart = tk.Button(master=frame, text="开始", command=lambda: tutest_procd(
        editArea1, editArea2, editArea3, dispArea))
    bstart.grid(padx=40, row=0, column=2, columnspan=2, sticky='nsew')
    bquit = tk.Button(master=frame, text="退出", command=root.destroy)
    bquit.grid(padx=40, row=1, column=2, columnspan=2, sticky='nsew')
    bstop = tk.Button(master=frame, text="停止闪烁",
                      command=lambda: StopFlash())
    bstop.grid(padx=10, pady=10, row=8, column=0,
               columnspan=4, sticky='nsew')
    root.mainloop()


# ******* Run *******
today, yesterday = get_date()
init_tk()
