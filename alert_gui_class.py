# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 14:33:37 2017

@author: lyb
"""
import win32gui as wg
import win32con as wc
import tushare as ts
import tkinter as tk

from os import path, getcwd
from time import sleep
from dateu import get_date
from numpy import array
from datetime import datetime
from retrying import retry
from tkinter.scrolledtext import ScrolledText

import _thread

testStatus = True

# ******* Classes *******


class MyGUI:
    """
    Initialize widgets
    """

    def __init__(self, par):
        """Set contents for all widgets"""
        self.master = master = tk.Tk()
        self.frame = tk.Frame(master=self.master)
        self.init_win(par)
        self.editArea1 = self.init_inp(0, 1, "周期分钟   -->", par.dt)
        self.editArea2 = self.init_inp(1, 1, "百分阈值   -->", par.pc)
        self.editArea3 = self.init_inp(2, 1, "上个交易日 -->", par.y)
        self.dispArea = self.init_disp()

        self.btnBg = tk.Button(self.frame, text="开始",
                               command=lambda: tutest_procd(self, par))
        self.btnBg.grid(padx=40, row=0, column=2, columnspan=2, sticky='nsew')
        self.btnQt = tk.Button(self.frame, text="退出", command=master.destroy)
        self.btnQt.grid(padx=40, row=1, column=2, columnspan=2, sticky='nsew')

    def init_win(self, par):
        """Main window"""
        self.master.geometry('600x300+10+10')
        self.master.title(par.ttl)
        self.frame.grid(row=0, column=0, sticky='nsew')
        tk.Grid.rowconfigure(self.master, 0, weight=1)
        tk.Grid.columnconfigure(self.master, 0, weight=1)

    def init_inp(self, ro, co, label, txt):
        """Input area"""
        tk.Label(master=self.frame, text=label).grid(
            padx=10, row=ro, column=co - 1, sticky='w')
        edit_area = tk.Entry(master=self.frame, width=15)
        edit_area.grid(padx=40, row=ro, column=co, sticky='w')
        edit_area.insert(0, txt)
        return edit_area

    def init_disp(self):
        """Output area"""
        disp_area = ScrolledText(
            master=self.frame, wrap=tk.WORD, width=60, height=10)
        disp_area.grid(padx=10, pady=10, row=3, column=0,
                       columnspan=4, rowspan=4, sticky='nsew')
        disp_area.bind("<1>", lambda event: disp_area.focus_set())
        disp_area.insert('end', '等待指示！')
        disp_area.configure(state='disabled')
        tk.Grid.rowconfigure(self.frame, 3, weight=1)
        tk.Grid.columnconfigure(self.frame, 0, weight=1)
        return disp_area

    def update_disp(self, txt):
        """Output area update"""
        self.dispArea.configure(state='normal')
        self.dispArea.insert('end', txt + '\n')
        self.dispArea.configure(state='disabled')
        self.dispArea.see('end')
        self.dispArea.update()

    def delete_disp(self):
        """Output area clean"""
        self.dispArea.configure(state='normal')
        self.dispArea.delete('1.0', 'end')
        self.dispArea.configure(state='disabled')
        self.dispArea.update()


class MyParams:
    """
    Initialize parameters:
    tday - this trade day
    yday - last trade day
    dt_min - time interval
    ts_perc - percent threshold value
    txt - input file of stock lists
    """

    def __init__(self, tday, yday, dt_min, ts_perc, txt):
        cpath = path.basename(path.normpath(getcwd()))
        self.ttl = str(datetime.now()) + ' - ' + cpath
        self.t = tday
        self.y = yday
        self.dt = dt_min
        self.pc = ts_perc
        with open(txt) as f:
            self.ln = [r.split()[0] for r in f]


class MyHistQts:
    """
    Get history volume and information
    """

    def __init__(self, gui, par):
        self.info_h = []
        self.vol_h = []
        self.get_hist_vol(gui, par)

    def get_hist_vol(self, gui, par):
        for i in range(len(par.ln)):
            self.vol_h.append(0)
        for ir in range(len(par.ln)):
            dfy = ts.get_hist_data(par.ln[ir], start=par.y, end=par.y)
            if dfy.empty:
                gui.update_disp(str(par.ln[ir]) + ' ' + par.y + ' 停牌')
            else:
                self.vol_h[ir] = dfy.iloc[0]['volume']
                # self.info_h = self.info_h + str(par.ln[ir]) + ' ' + par.y + \
                #         ' 日交易量为 ' + str(self.vol_h[ir]) + '\n'
        self.vol_h = array(self.vol_h)
        par.ln = array(par.ln)[self.vol_h != 0].tolist()
        self.vol_h = self.vol_h[self.vol_h != 0].tolist()


class MyRealQts:
    """
    Get real-time stock information
    """

    def __init__(self, par):
        self.vol = []
        self.amt = []
        self.name = []
        self.lctime = []
        self.prc = []
        self.prcc = []
        self.get_real_vol(par)

    def get_real_vol(self, par):
        """Get real-time volume"""
        dft = self.ult_get_realtime_quotes(par.ln)
        self.vol = [float(i) / 100 for i in dft['volume'].tolist()]
        self.amt = [float(i) for i in dft['amount'].tolist()]
        self.name = dft['name'].tolist()
        self.lctime = dft['time'].tolist()
        self.get_price_change(dft)
        # self.info = today + ' ' + str(self.lctime) + ' 时成交量为 ' + str(self.vol)

    def get_price_change(self, dft):
        """Get real-time price change wrt. the close price of yesterday"""
        prc_hist = [float(i) for i in dft['pre_close'].tolist()]
        self.prc = [float(i) for i in dft['price'].tolist()]
        self.prcc = [i for i in range(len(self.prc))]
        for ir in range(len(self.prc)):
            self.prcc[ir] = (self.prc[ir] - prc_hist[ir]) / prc_hist[ir]

    @retry
    def ult_get_realtime_quotes(self, lines):
        """Retry ultimate times"""
        return ts.get_realtime_quotes(lines)


class AlertStatus:
    """
    Compute real-time volume within a short period, compare it with the voluem
    of last trade day, and alert if condition is satisfied.
    """

    def __init__(self, hist, rd1, rd2, gui, par):
        self.status = []
        for i in range(len(par.ln)):
            self.status.append(False)
        self.cal_vol(hist, rd1, rd2, gui, par)

    def cal_vol(self, hist, rd1, rd2, gui, par):
        for ir in range(len(rd1.vol)):
            rt = (rd2.vol[ir] - rd1.vol[ir]) / hist.vol_h[ir] * 100.
            at = rd2.amt[ir] - rd1.amt[ir]

            try:
                pt = (rd2.prc[ir] - rd1.prc[ir]) / rd1.prc[ir]
            except ZeroDivisionError:
                pt = 0.

            if rt > par.pc:
                atxt = chinese(str(rd2.name[ir]), 9) + \
                       "{:<10}".format(str(rd2.lctime[ir])) + \
                       "{:<9}".format(str(format(rd2.prcc[ir], '.2%'))) + \
                       "{:<11}".format(str(format(pt, '.2%'))) + \
                       "{:<8}".format(str(at)) + \
                       ' || ' + str(par.dt) + '分钟内成交量为昨日' + \
                       "{:<8}".format(str(format(rt / 100., '.2%')))
                gui.update_disp(atxt)
                self.flash(par.ttl)
                self.status[ir] = True

    @staticmethod
    def flash(ttl):
        """Flash the caption and taskbar icon"""
        cur_win = wg.FindWindow(None, ttl)
        wg.FlashWindowEx(cur_win, wc.FLASHW_STOP, 0, 0)
        cur_foreground = wg.GetForegroundWindow()
        if cur_win == cur_foreground:
            taskbar = wg.FindWindow("Shell_TrayWnd", None)
            wg.SetForegroundWindow(taskbar)
        wg.FlashWindowEx(cur_win, wc.FLASHW_ALL | wc.FLASHW_TIMERNOFG, 0, 0)


# ******* Functions *******
def fo_nomerge(name):
    i = 0
    while path.exists(name + '-' + str(i) + '.txt'):
        i += 1
    fo = open(name + '-' + str(i) + '.txt', 'w')
    return fo


def chinese(oldstr, length):
    """
    To solve the chinese character alignment issue in python.
    The display and count differences in length is automatically compensated.
    """
    count = 0
    for s in oldstr:
        if ord(s) > 127:
            count += 1
    newstr = oldstr
    if length > count:
        newstr = '{0:{wd}}'.format(oldstr, wd=length - count)
    return newstr


def trig_alert(gui, par):
    """
    Check the status of cal_vol every specific time interval
    """
    global testStatus
    hist = MyHistQts(gui, par)
    info = '************* 开始监控盘中实时交易量 *************\n' + \
           chinese('股名', 9) + chinese('时间', 10) + chinese('涨幅', 9) + \
           chinese('瞬时涨幅', 11) + chinese('成交金额', 8)
    gui.update_disp(info)

    real_data1 = MyRealQts(par)
    count = 0
    sleep(int(par.dt * 60))

    # fo = fo_nomerge('AlertStatus')
    # fo.write(str(count) + '分钟：' + str(par.ln) + '\n')
    while float(count) < 420 / par.dt:
        real_data2 = MyRealQts(par)
        if testStatus:
            real_data2.vol = [i + 2000 for i in real_data1.vol]  # Only for test
        AlertStatus(hist, real_data1, real_data2, gui, par)
        real_data1 = real_data2
        count = count + 1
        # fo.write(str(count) + '分钟：' + str(alert.status) + '\n')
        sleep(int(par.dt * 60))

    # fo.close()
    gui.update_disp('监控完成！')


def tutest_procd(gui, par):
    try:
        par.dt = float(gui.editArea1.get())
        par.pc = float(gui.editArea2.get())
        par.yday = gui.editArea3.get()
        datetime.strptime(par.yday, '%Y-%m-%d')
    except ValueError:
        gui.update_disp("参数格式不正确！请重新输入！！!")
        return

    gui.delete_disp()
    gui.update_disp(" 监控股票 " + str(par.ln))
    _thread.start_new_thread(trig_alert, (gui, par))


today, yesterday = get_date()
my_par = MyParams(today, yesterday, str(2), str(2), "股票代码.txt")
my_gui = MyGUI(my_par)
my_gui.master.mainloop()
