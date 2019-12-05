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

Noon_Begin = "11:30:00"
Noon_End = "13:00:00"
Closing_Time = "15:00:00"
day_time = time.strftime('%Y%m%d', time.localtime(time.time()))

root_path = "D:\\Workspace\\Python\\Stocks"
EHBFfile_path = os.path.join(root_path, "Result", "Stocks", "EHBF_Analyze_Result.csv")
dailydata_path = os.path.join(root_path, 'Data', 'daily_data') 
noondata_path = os.path.join(dailydata_path, "noon_data.csv")
nightdata_path = os.path.join(dailydata_path, "night_data.csv")
resultdata_path = os.path.join(root_path, "Result", "Daily")
if __name__=="__main__":
    if(not os.path.exists(resultdata_path)):
        os.mkdir(resultdata_path)


def timesub(time1, time2):
    hour1 = float(time1[0:2])
    minute1 = float(time1[3:5])
    second1 = float(time1[6:8])
    hour2 = float(time2[0:2])
    minute2 = float(time2[3:5])
    second2 = float(time2[6:8])
    return (hour1-hour2)*3600+(minute1-minute2)*60+(second1-second2)


def read_csvfile(filename):
    if(os.path.exists(filename)):
        with open(filename, 'r') as fp:
            data_list = list(csv.reader(fp))
            return data_list[0], data_list[1:]
    else:
        return [], []


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            if(row_item!=[]):
                fp.write(",".join([str(item) for item in row_item]) + "\n")


def gen_tscode(stockcode):
    code = ""
    if(stockcode[0]=="0"):
        code=stockcode+".SZ"
    elif(stockcode[0]=="6"):
        code=stockcode+".SH"
    return code


def gen_163code(stockcode):
    code = ""
    if(stockcode[0]=="0"):
        code = "1"+stockcode
    elif(stockcode[0]=="6"):
        code = "0"+stockcode
    return code


def isMarketOpen():
    df = tspro.trade_cal(exchange='', start_date=day_time, end_date=day_time)
    df_list = df.values.tolist()
    if(df_list[0][2]==1):
        return True
    else:
        return False

def get_realtimedata(filename):
    title = ["code", "name", "changepercent", "trade", "open", "high", "low", "settlement", "volumn", "turnoverratio", "amount", "per", "pb", "mktcap", "nmc"]
    for ii in range(5):
        try:
            df = ts.get_today_all()
            print()
            break
        except Exception as e:
            print(e)
            time.sleep(1200)
            continue
    df_list = df.values.tolist()
    for ii in reversed(range(len(df_list))):
        if((df_list[ii][0][:3] not in ["000", "600"]) or (df_list[ii][6]==0.0)):
            df_list.pop(ii)
            continue
        for jj in range(ii):
            if(df_list[jj][0]==df_list[ii][0]):
                df_list.pop(ii)
                break
    write_csvfile(filename, title, df_list)


def morningfall_select():
    resultfile_path = os.path.join(resultdata_path, "morningfall_select.csv")
    get_realtimedata(noondata_path)
    title = ["股票名称", "当前涨跌幅", "获利持仓比例", "百日位置(%)", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度"]
    resultdata_list = []
    _, noondata_list = read_csvfile(noondata_path)
    _, EHBFdata_list = read_csvfile(EHBFfile_path)
    for item in noondata_list:
        open_range = (float(item[4])-float(item[7]))/float(item[7])*100
        cylinder_range = (float(item[3])-float(item[4]))/float(item[7])*100
        downshadow_range = (min(float(item[4]), float(item[3]))-float(item[6]))/float(item[7])*100
        upshadow_range = (float(item[5])-max(float(item[4]), float(item[3])))/float(item[7])*100
        if((cylinder_range<-3) and (open_range<0)):
            earnratio = "-1"
            reboundrange = "-1"
            for EHBFitem in EHBFdata_list:
                if(EHBFitem[0].split('_')[-1][-6:]==item[0]):
                    reboundrange = EHBFitem[2]
                    earnratio = EHBFitem[3]
            resultdata_list.append([item[1]+"_"+item[0], item[2], earnratio, reboundrange, round(open_range,2), round(cylinder_range,2), round(downshadow_range,2), round(upshadow_range,2)])
    if(resultdata_list):
        write_csvfile(resultfile_path, title, resultdata_list)


def afternoonfall_select():
    resultfile_path = os.path.join(resultdata_path, "afternoonfall_select.csv")
    get_realtimedata(nightdata_path)
    title = ["股票名称", "今日涨跌幅", "获利持仓比例", "百日位置(%)", "上午涨跌幅", "午后涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度"]
    resultdata_list = []
    _, nightdata_list = read_csvfile(nightdata_path)
    _, noondata_list = read_csvfile(noondata_path)
    _, EHBFdata_list = read_csvfile(EHBFfile_path)
    for nightitem in nightdata_list:
        afternoon_range = 0
        noon_range = 0
        for noonitem in noondata_list:
            if(noonitem[0]==nightitem[0]):
                noon_range = float(noonitem[2])
                afternoon_range = float(nightitem[2])-float(noonitem[2])
                break
        open_range = (float(nightitem[4])-float(nightitem[7]))/float(nightitem[7])*100
        cylinder_range = (float(nightitem[3])-float(nightitem[4]))/float(nightitem[7])*100
        downshadow_range = (min(float(nightitem[4]), float(nightitem[3]))-float(nightitem[6]))/float(nightitem[7])*100
        upshadow_range = (float(nightitem[5])-max(float(nightitem[4]), float(nightitem[3])))/float(nightitem[7])*100
        if((afternoon_range<-3) and (open_range<0) and (noon_range<0)):
            earnratio = "-1"
            reboundrange = "-1"
            for EHBFitem in EHBFdata_list:
                if(EHBFitem[0].split('_')[-1][-6:]==nightitem[0]):
                    reboundrange = EHBFitem[2]
                    earnratio = EHBFitem[3]
            resultdata_list.append([nightitem[1]+"_"+nightitem[0], nightitem[2], earnratio, reboundrange, noon_range, afternoon_range, round(open_range,2), round(cylinder_range,2), round(downshadow_range,2), round(upshadow_range,2)])
    if(resultdata_list):
        write_csvfile(resultfile_path, title, resultdata_list)


def alldayfall_select():
    resultfile_path = os.path.join(resultdata_path, "alldayfall_select.csv")
    title = ["股票名称", "今日涨跌幅", "获利持仓比例", "百日位置(%)", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度"]
    resultdata_list = []
    _, nightdata_list = read_csvfile(nightdata_path)
    _, EHBFdata_list = read_csvfile(EHBFfile_path)
    for nightitem in nightdata_list:
        open_range = (float(nightitem[4])-float(nightitem[7]))/float(nightitem[7])*100
        cylinder_range = (float(nightitem[3])-float(nightitem[4]))/float(nightitem[7])*100
        downshadow_range = (min(float(nightitem[4]), float(nightitem[3]))-float(nightitem[6]))/float(nightitem[7])*100
        upshadow_range = (float(nightitem[5])-max(float(nightitem[4]), float(nightitem[3])))/float(nightitem[7])*100
        if((cylinder_range<-4) and (open_range<0)):
            earnratio = "-1"
            reboundrange = "-1"
            for EHBFitem in EHBFdata_list:
                if(EHBFitem[0].split('_')[-1][-6:]==nightitem[0]):
                    reboundrange = EHBFitem[2]
                    earnratio = EHBFitem[3]
            resultdata_list.append([nightitem[1]+"_"+nightitem[0], nightitem[2], earnratio, reboundrange, round(open_range,2), round(cylinder_range,2), round(downshadow_range,2), round(upshadow_range,2)])
    if(resultdata_list):
        write_csvfile(resultfile_path, title, resultdata_list)


def clear_data():
    for filename in os.listdir(dailydata_path):
        filepath = os.path.join(dailydata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    for filename in os.listdir(resultdata_path):
        filepath = os.path.join(resultdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def main():
    if(isMarketOpen()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMorningfall_Select Begin!")
        morningfall_select()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMorningfall_Select Finished!")
        time.sleep(5*3600)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tafternoonfall_Select Begin!")
        afternoonfall_select()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tafternoonfall_Select Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\talldayfall_Select Begin!")
        alldayfall_select()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\talldayfall_Select Finished!")


if(__name__ == "__main__"):
    main()