import tkinter
import tkinter.messagebox
import tushare as ts
import threading
import time
import datetime
import math
import os
import csv


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")
day_time = time.strftime('%Y%m%d', time.localtime(time.time()))

Bidding_Time = "09:00:00"
Opening_Time = "09:30:00"
Noon_Begin = "11:30:00"
Noon_End = "13:00:00"
Closing_Time = "15:00:00"

root_path = "D:\\Workspace\\Python\\Stocks"
stocktrade_filepath = os.path.join(root_path, "trade.csv")

def read_csvfile(filename):
    with open(filename, 'r') as fp:
        data_list = list(csv.reader(fp))
        return data_list[0], data_list[1:]


def timesub(time1, time2):
    hour1 = float(time1[0:2])
    minute1 = float(time1[3:5])
    second1 = float(time1[6:8])
    hour2 = float(time2[0:2])
    minute2 = float(time2[3:5])
    second2 = float(time2[6:8])
    return (hour1-hour2)*3600+(minute1-minute2)*60+(second1-second2)


def getTradeBook():
    title, trade_list = read_csvfile(stocktrade_filepath)
    stockinfo_list = []
    pretrade_list = []
    for ii in range(len(trade_list)):
        stockinfo = trade_list[ii][0]
        pretrade = float(trade_list[ii][3])
        if(stockinfo[-6] in ['0', '6']):
            stockinfo_list.append(stockinfo)
            pretrade_list.append(pretrade)
    return stockinfo_list, pretrade_list


def price_Monitor(stockinfo_list, buyprice_list, sellprice_list):
# 价格监控
    stockcode_list = [item[-6:] for item in stockinfo_list]
    stocknum = len(stockcode_list)
    price_list = [0 for ii in range(stocknum)]
    time_delay = 0
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if(min(df_time)>=Opening_Time):
            for ii in range(stocknum):
                price_list[ii] = float(df[df.code==stockcode_list[ii]]['pre_close'].values[0])
            time_delay = 0
            break
        else:
            time_delay = timesub(Opening_Time, min(df_time))
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if((max(df_time) >= Noon_Begin) and (min(df_time) < Noon_End)):
            time_delay = timesub(Noon_End, min(df_time))
            continue
        if(max(df_time) >= Closing_Time):
            break
        time_delay = 60 - (float(max(df_time)[-2:])%60)
        for ii in range(stocknum):
            price_list[ii] = float(df[df.code==stockcode_list[ii]]['price'].values[0])
            if(price_list[ii]<=buyprice_list[ii]):
                print("\a") 
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t买入: ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))
            if(price_list[ii]>=sellprice_list[ii]):
                print("\a") 
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t卖出: ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))


def grid_Monitor(stockinfo_list, baseprice_list):
# 网格交易法 + MACD 确定买入点
    stockcode_list = [item[-6:] for item in stockinfo_list]
    stocknum = len(stockcode_list)
    gridincrease = 0.03
    griddrop = 0.03
    price_list = [0 for ii in range(stocknum)]
    EMA12_list = [0 for ii in range(stocknum)]
    EMA26_list = [0 for ii in range(stocknum)]
    DEA9_list = [0 for ii in range(stocknum)]
    DIFF_list = [0 for ii in range(stocknum)]
    MACD_list = [0 for ii in range(stocknum)]
    price_list = [0 for ii in range(stocknum)]
    MACDpre_list = [0 for ii in range(stocknum)]
    time_delay = 0
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if(min(df_time)>=Opening_Time):
            for ii in range(stocknum):
                price_list[ii] = float(df[df.code==stockcode_list[ii]]['pre_close'].values[0])
                EMA12_list[ii] = price_list[ii]
                EMA26_list[ii] = price_list[ii]
            time_delay = 0
            break
        else:
            time_delay = timesub(Opening_Time, min(df_time))

    buyprice_list = [(1-griddrop)*item for item in baseprice_list]
    sellprice_list = [(1+gridincrease)*item for item in baseprice_list]
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if((max(df_time) >= Noon_Begin) and (min(df_time) < Noon_End)):
            time_delay = timesub(Noon_End, min(df_time))
            continue
        if(max(df_time) >= Closing_Time):
            break
        time_delay = 60 - (float(max(df_time)[-2:])%60)
        for ii in range(stocknum):
            price_list[ii] = float(df[df.code==stockcode_list[ii]]['price'].values[0])
            price_list[ii] = float(df[df.code==stockcode_list[ii]]['price'].values[0])
            EMA12_list[ii] = 11/13*EMA12_list[ii] + 2/13*price_list[ii]
            EMA26_list[ii] = 25/27*EMA26_list[ii] + 2/27*price_list[ii]
            DIFF_list[ii] = EMA12_list[ii] - EMA26_list[ii]
            DEA9_list[ii] = 8/10*DEA9_list[ii] + 2/10*DIFF_list[ii]
            MACDpre_list[ii] = MACD_list[ii]
            MACD_list[ii] = DIFF_list[ii]-DEA9_list[ii]
            MACD_predict = math.ceil(MACD_list[ii]/(MACDpre_list[ii]-MACD_list[ii]))
#            if((price_list[ii]<=buyprice_list[ii]) and ((MACDpre_list[ii]>0) and (MACD_list[ii]<MACDpre_list[ii]) and MACD_predict<3)):
            if(price_list[ii]<=buyprice_list[ii]):
                buyprice_list[ii] = price_list[ii]*(1-griddrop)
                sellprice_list[ii] = price_list[ii]*(1+gridincrease)
                print("\a")
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t买入: ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))
#            if(price_list[ii]>=sellprice_list[ii] and ((MACDpre_list[ii]<0) and (MACD_list[ii]>MACDpre_list[ii]) and MACD_predict<3)):
            if(price_list[ii]>=sellprice_list[ii]):
                buyprice_list[ii] = price_list[ii]*(1-griddrop)
                sellprice_list[ii] = price_list[ii]*(1+gridincrease)
                print("\a") 
                print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t卖出: ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))


def tradegrid_Moniter():
    stockinfo_list, pretrade_list = getTradeBook()
    grid_Monitor(stockinfo_list, pretrade_list)


def tshape_Monitor(stockinfo_list):
# 日内涨跌幅 可日内做T
    stockcode_list = [item[-6:] for item in stockinfo_list]
    dailydrop = 0.02
    dailyincrease = 0.02
    stocknum = len(stockinfo_list)
    preclose_list = [0 for ii in range(stocknum)]
    currentprice_list = [0 for ii in range(stocknum)]
    time_delay = 0
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if(min(df_time)>=Opening_Time):
            for ii in range(stocknum):
                preclose_list[ii] = float(df[df.code==stockcode_list[ii]]['pre_close'].values[0])
            time_delay = 0
            break
        else:
            time_delay = timesub(Opening_Time, min(df_time))
    price_Monitor(stockinfo_list, [(1-dailydrop)*item for item in preclose_list], [(1+dailyincrease)*item for item in preclose_list])


def MACD_Monitor(stockinfo_list):
# 分时 MACD 交易法
    Stable_Time = "09:50:00"
    time_period = 60
    DEA_Limit = 0.003
    stocknum = len(stockinfo_list)
    stockcode_list = [item[-6:] for item in stockinfo_list]
    EMA12_list = [0 for ii in range(stocknum)]
    EMA26_list = [0 for ii in range(stocknum)]
    DEA9_list = [0 for ii in range(stocknum)]
    DIFF_list = [0 for ii in range(stocknum)]
    MACD_list = [0 for ii in range(stocknum)]
    price_list = [0 for ii in range(stocknum)]
    MACDpre_list = [0 for ii in range(stocknum)]
    time_delay = 0
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
#        print(min(df_time))
        if(min(df_time)>=Opening_Time):
            for ii in range(stocknum):
                price_list[ii] = float(df[df.code==stockcode_list[ii]]['pre_close'].values[0])
                EMA12_list[ii] = price_list[ii]
                EMA26_list[ii] = price_list[ii]
            time_delay = 0
            break
        else:
            time_delay = timesub(Opening_Time, min(df_time))

    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if((max(df_time) >= Noon_Begin) and (min(df_time) < Noon_End)):
            time_delay = timesub(Noon_End, min(df_time))
            continue
        if(max(df_time) >= Closing_Time):
            break
        time_delay = time_period - (float(max(df_time)[-2:])%time_period)
        for ii in range(stocknum):
            price_list[ii] = float(df[df.code==stockcode_list[ii]]['price'].values[0])
            EMA12_list[ii] = 11/13*EMA12_list[ii] + 2/13*price_list[ii]
            EMA26_list[ii] = 25/27*EMA26_list[ii] + 2/27*price_list[ii]
            DIFF_list[ii] = EMA12_list[ii] - EMA26_list[ii]
            DEA9_list[ii] = 8/10*DEA9_list[ii] + 2/10*DIFF_list[ii]
            MACDpre_list[ii] = MACD_list[ii]
            MACD_list[ii] = DIFF_list[ii]-DEA9_list[ii]
            if(min(df_time)<=Stable_Time):
                continue
#            print(stockinfo_list[ii] + "\tDEA:" + str(DEA9_list[ii]))
#            print(stockinfo_list[ii] + "\tDIFF: " + str(DIFF_list[ii]))
#            print(stockinfo_list[ii] + "\tMACD: " + str(MACD_list[ii]))
#            print(stockinfo_list[ii] + "\tprice: " + str(price_list[ii]))
#            print(stockinfo_list[ii] + "\tDEA/price: " + str(DEA9_list[ii]/price_list[ii]))
#            if((MACDpre_list[ii]>0) and (MACD_list[ii]<MACDpre_list[ii]) and (DEA9_list[ii]>0) and (abs(DEA9_list[ii])>DEA_Limit*price_list[ii])):
            if((MACDpre_list[ii]>0) and (MACD_list[ii]<MACDpre_list[ii])):
                MACD_predict = math.ceil(MACD_list[ii]/(MACDpre_list[ii]-MACD_list[ii]))
                if(MACD_predict<3):
                    print("\a") 
                    print("分时 MACD 成交 死叉卖出")
                    print("预测交叉倒计时(*" + str(time_period) + "s): " + str(MACD_predict))
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t卖出: ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))
                    cross_price = (DEA9_list[ii]-11/13*EMA12_list[ii]+25/27*EMA26_list[ii])/(2/13-2/27)
                    parallel_price = (5/8*MACD_list[ii]+DEA9_list[ii]-11/13*EMA12_list[ii]+25/27*EMA26_list[ii])/(2/13-2/27)
                    print("相交价格: " + str(round(cross_price,2)) + " ; 平行价格: " + str(round(parallel_price, 2)))
                    print(DEA9_list[ii])
#            if((MACDpre_list[ii]<0) and (MACD_list[ii]>MACDpre_list[ii]) and (DEA9_list[ii]<0) and (abs(DEA9_list[ii])>DEA_Limit*price_list[ii])):
            if((MACDpre_list[ii]<0) and (MACD_list[ii]>MACDpre_list[ii])):
                MACD_predict = math.ceil(MACD_list[ii]/(MACDpre_list[ii]-MACD_list[ii]))
                if(MACD_predict<3):
                    print("\a")
                    print("分时 MACD 成交 金叉买入")
                    print("预测交叉倒计时(*" + str(time_period) + "s): " + str(MACD_predict))
                    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t买入 ' + stockinfo_list[ii] + "; 价格: " + str(price_list[ii]))
                    cross_price = (DEA9_list[ii]-11/13*EMA12_list[ii]+25/27*EMA26_list[ii])/(2/13-2/27)
                    parallel_price = (5/8*MACD_list[ii]+DEA9_list[ii]-11/13*EMA12_list[ii]+25/27*EMA26_list[ii])/(2/13-2/27)
                    print("相交价格: " + str(round(cross_price,2)) + " ; 平行价格: " + str(round(parallel_price,2)))
                    print(DEA9_list[ii])


def tradeMACD_Moniter():
    stockinfo_list, _ = getTradeBook()
    MACD_Monitor(stockinfo_list)


def rebound_Monitor():
# 日内涨跌幅 可日内做T
    time_delay = 3600
    while(True):
        df = ts.get_today_all()
        for index, row in df.iterrows():
            if((row['code'][:3] in ["000", "600"]) and (row['low']!=0.0)):
                openrange = (row['open']-row['settlement'])/row['settlement']*100
                greenrange = (row['trade']-row['open'])/row['settlement']*100
                maxdroprange = (row['low']-row['settlement'])/row['settlement']*100
                dailyrange = row['changepercent']
                if((openrange>-2) and (maxdroprange<-5)):
                    reboundrange = (row['trade']-row['low'])/(row['settlement']-row['low'])
                    if(0.1<reboundrange):
                        print("\a")
                        print("股票代码: " + str(row['code']) + ", 股票名称: " + str(row['name']) + ", 当前涨跌幅: " + str(dailyrange) + ", 最大跌幅:" + str(maxdroprange))
        time.sleep(time_delay)


def wheel_Moniter():
#    stockinfo_list = ['HS300-中国石油_0601857', 'HS300-中国石化_0600028']
    stockinfo_list = ['HS300-中国银行_0601988', 'HS300-工商银行_0601398', 'HS300-建设银行_0601939', 'HS300-农业银行_0601288', 'HS300-交通银行_0601328', 'HS300-招商银行_0600036']
    stockcode_list = [item[-6:] for item in stockinfo_list]
    interval = 0.005
    stocknum = len(stockinfo_list)
    preclose_list = [0 for ii in range(stocknum)]
    price_list = [0 for ii in range(stocknum)]
    ratio_list = [0 for ii in range(stocknum)]
    time_delay = 0
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if(min(df_time)>=Opening_Time):
            for ii in range(stocknum):
                preclose_list[ii] = float(df[df.code==stockcode_list[ii]]['pre_close'].values[0])
            time_delay = 0
            break
        else:
            time_delay = timesub(Opening_Time, min(df_time))
    while(True):
        time.sleep(time_delay)
        df = ts.get_realtime_quotes(stockcode_list)
        df_time = df['time']
        if((max(df_time) >= Noon_Begin) and (min(df_time) < Noon_End)):
            time_delay = timesub(Noon_End, min(df_time))
            continue
        if(max(df_time) >= Closing_Time):
            break
        time_delay = 60 - (float(max(df_time)[-2:])%60)
        for ii in range(stocknum):
            price_list[ii] = float(df[df.code==stockcode_list[ii]]['price'].values[0])
            ratio_list[ii] = price_list[ii]/preclose_list[ii]
        if((max(ratio_list)-min(ratio_list))>interval):
            print("\a")
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\t卖出：' + stockinfo_list[ratio_list.index(max(ratio_list))] + '； 价格： ' + str(price_list[ratio_list.index(max(ratio_list))]) +  '买入: ' + stockinfo_list[ratio_list.index(min(ratio_list))] + "; 价格: " + str(price_list[ratio_list.index(min(ratio_list))]))


if(__name__ == "__main__"):
#    MACD_Monitor(["1巨人网络_1002558", "3森源电气_1002358", "4浙江交科_1002061", "5百隆东方_0601339", "6大晟文化_0600892", "7深圳惠程_1002168", "8华友钴业_0603799", "9金龙汽车600686", "10视觉中国000681", "11海容冷链603187", "12沃格光电603773", "13惠而浦600983"])
#    price_Monitor_list = []
#    price_Monitor_list.append(["视觉中国000681", 16.72, 18.13])
#    price_Monitor_list.append(["三友化工600409", 5.56, 6.03])
#    price_Monitor_list.append(["浙江交科002061", 5.80, 6.30])
#    price_Monitor_list.append(["九州通600998", 12.41, 13.45])
#    price_Monitor_list.append(["秋林股份600891", 1.45, 1.55])
#    price_Monitor_list.append(["大晟文化600892", 5.69, 6.00])
#    price_Monitor([item[0] for item in price_Monitor_list], [item[1] for item in price_Monitor_list], [item[2] for item in price_Monitor_list])
#    rebound_Monitor()
    tradegrid_Moniter()
#    tradeMACD_Moniter()