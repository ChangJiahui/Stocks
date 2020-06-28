#coding:utf-8
# _file & filename 单个文件路径		_path 文件夹路径
# stockdata_list 1行15列数据  0日期,1股票代码,2名称,3收盘价,4最高价,5最低价,6开盘价,7前收盘,8涨跌额,9涨跌幅,10换手率,11成交量,12成交金额,13总市值,14流通市值


import requests
import random
from bs4 import BeautifulSoup
import pandas as pd
import time
import datetime as dt
import os
import csv
import json
import math
import tushare as ts
import numpy as np
import execjs
import xlrd
import multiprocessing
import tunet
import urllib
import scipy
import scipy.stats as scistats
import statsmodels.api as sm


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()-24*3600))
#end_time = "20190621"
root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stockinfo.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data")
indexdata_path = os.path.join(root_path, "Data", "index_data")
HKdata_path = os.path.join(root_path, "Data", "stockHK_data")
Bdata_path = os.path.join(root_path, "Data", "stockAB_data")
margindata_path = os.path.join(root_path, "Data", "margin_data")
resultdata_path = os.path.join(root_path, "Result", "Stocks")
querydata_path = os.path.join(root_path, "Result", "Query")


def tunet_connect():
    with open("D:\\Workspace\\Python\\Stocks\\Code\\tunet.config") as fp:
        lines = fp.readlines()
        try:
            print(tunet.net.login(lines[0].strip(), lines[1].strip()))
            print(tunet.net.checklogin())
        except urllib.error.URLError as e:
            print(tunet.auth4.login(lines[0].strip(), lines[1].strip(), net=True))
            print(tunet.auth4.checklogin())
        except Exception as e:
            print(e)


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


def insert_csvfile(filename, data_list):
    title, stockdata_list = read_csvfile(filename)
    write_csvfile(filename, title, data_list+stockdata_list)


def read_xlsfile(filename):
    workbook = xlrd.open_workbook(filename)
    table = workbook.sheet_by_index(0)
    data_list = []
    for row_num in range(1, table.nrows):
        data_list.append(table.row_values(row_num))
    return data_list[0], data_list[1:]


def get_htmltext(url):
#    headers = {
#            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.81 Safari/537.36'
#    }
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            response = requests.get(url)
#            response = requests.get(url, headers=headers)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
                continue
            try:
                html_text = response.content.decode('utf-8-sig')
            except UnicodeDecodeError as e:
                html_text = response.content.decode('gbk')
#                print(e)
#            except NameError as e:
#                print(e)
#                html_text = ""
            return html_text
        except Exception as e:
            print(e)
    return ""


def download_file(url, filename):
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            data = requests.get(url)
            with open(filename, 'wb') as fp:
                chunk_size = 100000
                for chunk in data.iter_content(chunk_size):
                    fp.write(chunk)
#            print("Download Successfully: " + url)
            return True
        except Exception as e:
            print(e)
    return False


def get_jsvar(url, varname):
    response = get_htmltext(url)
    if(response.find(varname)!=-1):
        return execjs.compile(response).eval(varname)
    else:
        return None


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


def get_163data(stock163code, start_time, end_time, filename):
    download_url = "http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP".format(stock163code, start_time, end_time)
    if(download_file(download_url, filename)):
        return check_stockdata(filename)
    else:
        return False


def get_YahooHKdata(stockHcode, start_time, end_time, filename):
    title = ["日期", "开盘价", "最高价", "最低价", "收盘价", '复权收盘价', "成交量", "日涨跌幅"]
    yahoo_url = "https://query1.finance.yahoo.com/v7/finance/download/{}.HK?period1={}&period2={}&interval=1d&events=history".format(stockHcode[-4:],int(time.mktime(time.strptime(start_time,"%Y%m%d"))),int(time.mktime(time.strptime(end_time,"%Y%m%d")))+24*3600)
    if(download_file(yahoo_url, filename)):
        _, HKdata_list = read_csvfile(filename)
        HKdata_list.reverse()
        HKdata_list[-1].append(0)
        for ii in reversed(range(len(HKdata_list)-1)):
            if(HKdata_list[ii][1]=="null"):
                HKdata_list.pop(ii)
            else:
                HKdata_list[ii].append((float(HKdata_list[ii][5])/float(HKdata_list[ii+1][5])-1)*100)
        write_csvfile(filename, title, HKdata_list)
        return True
    return False


def check_stockdata(filename):
    title, stockdata_list = read_csvfile(filename)
    for ii in reversed(range(len(stockdata_list))):
        if((len(stockdata_list[ii])!=15) or (stockdata_list[ii][8]=="None") or (stockdata_list[ii][9]=="None") or (stockdata_list[ii][10]=="None") or (float(stockdata_list[ii][3])==0)):
            stockdata_list.pop(ii)
    for ii in range(1, len(stockdata_list)-1):
        if(float(stockdata_list[ii-1][7])!=float(stockdata_list[ii][3])):
            proportion = float(stockdata_list[ii-1][7])/float(stockdata_list[ii][3])
            for jj in range(ii, len(stockdata_list)):
                for kk in range(3,9):
                    stockdata_list[jj][kk] = round(float(stockdata_list[jj][kk])*proportion,2)
    if(stockdata_list==[]):
        os.remove(filename)
        return False
    else:
        write_csvfile(filename, title, stockdata_list)
        return True


def get_stockinfo():
# 得到股票信息字典列表 stock_dict{stocktype,stockname,stockcode, stock163code}
    def get_indexcomponent(stocktype, url, indexcomponent_file, compnum):
        for ii in range(5):
            download_file(url, indexcomponent_file)
            _, CSIdata_list = read_xlsfile(indexcomponent_file)
            stockdict_list = []
            for CSIitem in CSIdata_list:
                stockdict_list.append({'stocktype':stocktype, 'stockname': CSIitem[5], 'stockcode': CSIitem[4]})
            if(len(stockdict_list)<=compnum):
                time.sleep(600)
            else:
                break
        return stockdict_list
    HS300_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000300cons.xls"
    HS300_filepath = os.path.join(root_path, "Data", "HS300.xls")
    CSI500_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000905cons.xls"
    CSI500_filepath = os.path.join(root_path, "Data", "CSI500.xls")
    CSI1000_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000852cons.xls"
    CSI1000_filepath = os.path.join(root_path, "Data", "CSI1000.xls")
    CSIAll_url = "http://www.csindex.com.cn/uploads/file/autofile/cons/000902cons.xls"
    CSIAll_filepath = os.path.join(root_path, "Data", "CSIAll.xls")
    CSIAll_list = get_indexcomponent("CSIAll", CSIAll_url, CSIAll_filepath, 3000)
    CSI1000_list = get_indexcomponent("CSI1000", CSI1000_url, CSI1000_filepath, 950)
    HS300_list = get_indexcomponent("HS300", HS300_url, HS300_filepath, 280)
    CSI500_list = get_indexcomponent("CSI500", CSI500_url, CSI500_filepath, 460)
    with open(stockinfo_file, 'w') as fp:
        for ii in reversed(range(len(CSIAll_list))):
            if("ST" in CSIAll_list[ii]['stockname']):
                CSIAll_list.pop(ii)
                continue
#            if("*ST" in CSIAll_list[ii]['stockname']):
#                CSIAll_list[ii]['stockname'] = CSIAll_list[ii]['stockname'].replace("*ST", "XST")
            if(CSIAll_list[ii]['stockcode'][0] in ['0','6']):
                CSIAll_list[ii]['stock163code'] = gen_163code(CSIAll_list[ii]['stockcode'])
            else:
                CSIAll_list.pop(ii)
                continue
            for jj in range(len(CSI1000_list)):
                if(CSIAll_list[ii]['stockcode']==CSI1000_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = CSI1000_list[jj]['stocktype']
                    CSI1000_list.pop(jj)
                    break
            for jj in range(len(CSI500_list)):
                if(CSIAll_list[ii]['stockcode']==CSI500_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = CSI500_list[jj]['stocktype']
                    CSI500_list.pop(jj)
                    break
            for jj in range(len(HS300_list)):
                if(CSIAll_list[ii]['stockcode']==HS300_list[jj]['stockcode']):
                    CSIAll_list[ii]['stocktype'] = HS300_list[jj]['stocktype']
                    HS300_list.pop(jj)
                    break
            stockinfo = CSIAll_list[ii]['stocktype'] + "-" + CSIAll_list[ii]['stockname'] + '_' + CSIAll_list[ii]['stock163code']
            fp.write(stockinfo+"\n")


def isMarketOpen():
    for ii in range(3):
        try:
            df = tspro.trade_cal(exchange='', start_date=end_time, end_date=end_time)
            df_list = df.values.tolist()
            if(df_list[0][2]==1):
                return True
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    return False


def get_163indexdata():
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    for stockinfo in index_list:
        indexdata_file = os.path.join(indexdata_path,'{}.csv'.format(stockinfo))
        stock163code = stockinfo.split('_')[-1]
        get_163data(stock163code, start_time, end_time, indexdata_file)
    return True


def get_stockdata():
# 获得每只股票163历史数据
    with open(stockinfo_file, 'r') as fp:
        for stockinfo in fp.readlines():
            stockinfo = stockinfo.strip()
            if(stockinfo):
                stock163code = stockinfo.split('_')[-1]
                stockdata_file = os.path.join(stockdata_path,'{}.csv'.format(stockinfo))
                get_163data(stock163code, start_time, end_time, stockdata_file)


def EHBF_Analyze():
# 横盘天数 & 振幅 & EMA & earnratio & PE & PB
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日收盘价(元)", "当日涨跌幅(%)", "当日成交额(万元)", "当日换手率", "历史位置(%)", "百日位置(%)", "总交易日", "主力控盘比例", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "总市值", "流通市值", "10日标准差分位", "20日标准差分位", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅分位", "平均20日振幅分位", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日收盘价(元)", "当日涨跌幅(%)", "当日成交额(万元)", "当日换手率", "历史位置(%)", "百日位置(%)", "总交易日", "主力控盘比例", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "总市值", "流通市值", "10日标准差分位", "20日标准差分位", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅分位", "平均20日振幅分位", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    def EMA_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(100, len(stockdata_list))
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum]]
        EMA6 = 0
        EMA12 = 0
        EMA24 = 0
        for ii in reversed(range(perioddaynum)):
            EMA6 = 2/7*closingprice_list[ii] + 5/7*EMA6
            EMA12 = 2/13*closingprice_list[ii] + 11/13*EMA12
            EMA24 = 2/25*closingprice_list[ii] + 23/25*EMA24
        EMA6range = (closingprice/EMA6-1)*100
        EMA12range = (closingprice/EMA12-1)*100
        EMA24range = (closingprice/EMA24-1)*100
        return EMA6range, EMA12range, EMA24range

    def earnratio_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(500, len(stockdata_list)-1)
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
        upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+1]]
        lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+1]]
        obv_list = [float(item[10])/100 for item in stockdata_list[:perioddaynum+1]]
        for ii in reversed(range(len(obv_list))):
            obv_list[ii] = np.prod([(1-obv) for obv in obv_list[:ii]])*obv_list[ii]
        obv_dict = {}
        maxprice = max(upperprice_list)
        minprice = min(lowerprice_list)
        for price in [item/100 for item in range(round(minprice*100), round((maxprice+0.01)*100))]:
            obv_dict[price] = 0
        for ii in range(perioddaynum):
            aveobv = obv_list[ii]/((upperprice_list[ii]-lowerprice_list[ii]+0.01)*100)
            for price in [item/100 for item in range(round(lowerprice_list[ii]*100), round((upperprice_list[ii]+0.01)*100))]:
                obv_dict[price] += aveobv
        obv_sum = sum(obv_dict.values())
        supportobv = 0
        for price in [item/100 for item in range(round(max(closingprice*0.9,minprice)*100), round(closingprice*100))]:
            supportobv += obv_dict[price]
        supportratio = supportobv/obv_sum
        pressureobv = 0
        for price in [item/100 for item in range(round(closingprice*100), round(min(closingprice*1.1, maxprice)*100))]:
            pressureobv += obv_dict[price]
        pressureratio = pressureobv/obv_sum
        earnobv = 0
        for price in [item/100 for item in range(round(minprice*100), round(closingprice*100))]:
            earnobv += obv_dict[price]
        earnratio = earnobv/obv_sum
        cywobv = 0
        for ii in range(perioddaynum):
            if(upperprice_list[ii]==lowerprice_list[ii]):
                if(closingprice_list[ii]>closingprice_list[ii+1]):
                    cywobv += obv_list[ii]
                else:
                    cywobv -= obv_list[ii]
            else:
                cywobv += obv_list[ii]*(2*closingprice_list[ii]-upperprice_list[ii]-lowerprice_list[ii])/(upperprice_list[ii]-lowerprice_list[ii])
        cywratio = cywobv/obv_sum
        return pressureratio, supportratio, earnratio, cywratio
    
    def stable_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        perioddaynum = len(stockdata_list)-1
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
        stable5counter = perioddaynum
        stable10counter = perioddaynum
        stable20counter = perioddaynum
        for ii in range(1, perioddaynum):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.05*maxprice):
                stable5counter = ii
                break
        for ii in range(stable5counter, perioddaynum):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.1*maxprice):
                stable10counter = ii
                break
        for ii in range(stable10counter, perioddaynum):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.2*maxprice):
                stable20counter = ii
                break
        return stable5counter, stable10counter, stable20counter

    def std_Analyze(stockdata_list):
        N1 = 10
        N2 = 20
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(1000, len(stockdata_list)-N2)
        if(perioddaynum<300):
            return 0.5, 0.5
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
        std1_list = [0]*perioddaynum
        std2_list = [0]*perioddaynum
        for ii in range(perioddaynum):
            std1_list[ii] = np.std(closingprice_list[ii:ii+N1])/np.mean(closingprice_list[ii:ii+N1])*100
            std2_list[ii] = np.std(closingprice_list[ii:ii+N2])/np.mean(closingprice_list[ii:ii+N2])*100
        std1sort_list = sorted(std1_list)
        std2sort_list = sorted(std2_list)
        std1dist = std1sort_list.index(std1_list[0])/perioddaynum
        std2dist = std2sort_list.index(std2_list[0])/perioddaynum
        return std1dist, std2dist

    def amplitude_Analyze(stockdata_list):
        N1 = 10
        N2 = 20
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(1000, len(stockdata_list)-N2)
        if(perioddaynum<300):
            return 0.5, 0.5
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
        upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N2]]
        lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N2]]
        amp1_list = [0]*perioddaynum
        amp2_list = [0]*perioddaynum
        for ii in range(perioddaynum):
            amp1_list[ii] = np.mean([(upperprice_list[jj]-lowerprice_list[jj])/closingprice_list[jj] for jj in range(ii, ii+N1)])
            amp2_list[ii] = np.mean([(upperprice_list[jj]-lowerprice_list[jj])/closingprice_list[jj] for jj in range(ii, ii+N2)])
        amp1sort_list = sorted(amp1_list)
        amp2sort_list = sorted(amp2_list)
        amp1dist = amp1sort_list.index(amp1_list[0])/perioddaynum
        amp2dist = amp2sort_list.index(amp2_list[0])/perioddaynum
        return amp1dist, amp2dist

    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = len(stockdata_list)
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange1 = (closingprice-minprice)/(maxprice-minprice)*100
    closingprice_list = [float(item[3]) for item in stockdata_list[:100]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange2 = (closingprice-minprice)/(maxprice-minprice)*100
    stable5counter, stable10counter, stable20counter = stable_Analyze(stockdata_list)
    EMA6range, EMA12range, EMA24range = EMA_Analyze(stockdata_list)
    std10, std20 = std_Analyze(stockdata_list)
    pressureratio, supportratio, earnratio, cywratio = earnratio_Analyze(stockdata_list)
    amplitude10, amplitude20 = amplitude_Analyze(stockdata_list)
    drop30range = (closingprice/closingprice_list[min(30,perioddaynum-1)]-1)*100
    return [stockinfo, closingprice, stockdata_list[0][9], stockdata_list[0][12], stockdata_list[0][10], reboundrange1, reboundrange2, len(stockdata_list), cywratio, earnratio, pressureratio, supportratio, stockdata_list[0][13], stockdata_list[0][14], std10, std20, stable5counter, stable10counter, stable20counter, amplitude10, amplitude20, EMA6range, EMA12range, EMA24range, drop30range]


def value_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "value_Model_Select.csv")
    title = ["股票名称", "市净率(pb)", "市盈率(pe)", "pe(TTM)", "市销率(ps)", "ps(TTM)", "股权质押比例"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append([filename.split('.')[0]])
    for jj in range(3):
        try:
            df_todays = tspro.daily_basic(trade_date=end_time, fields='ts_code,pe,pe_ttm,pb,ps,ps_ttm')
            for ii in reversed(range(len(resultdata_list))):
                stockcode = resultdata_list[ii][0][-6:]
                stock_df = df_todays[df_todays.ts_code.str.contains(stockcode)]
                stock_pb = np.nan
                stock_pe = np.nan
                stock_pettm = np.nan
                stock_ps = np.nan
                stock_psttm = np.nan
                if(not stock_df.empty):
                    stock_pb = stock_df["pb"].values[0]
                    stock_pe = stock_df["pe"].values[0]
                    stock_pettm = stock_df["pe_ttm"].values[0]
                    stock_ps = stock_df["ps"].values[0]
                    stock_psttm = stock_df["ps_ttm"].values[0]
                if((0<(stock_pettm*stock_pb)<50) and (0<(stock_pe*stock_pb)<50)):
                    resultdata_list[ii] = resultdata_list[ii] + [stock_pb, stock_pe, stock_pettm, stock_ps, stock_psttm]
                else:
                    resultdata_list.pop(ii)
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    for ii in reversed(range(len(resultdata_list))):
        time.sleep(random.choice([1.2,2]))
        stockcode = resultdata_list[ii][0][-6:]
        stock_pledge = np.nan
        for jj in range(3):
            try:
                df_pledge = tspro.pledge_stat(ts_code=gen_tscode(stockcode))
                if(not df_pledge.empty):
                    stock_pledge = df_pledge["pledge_ratio"].values[0]
                break
            except Exception as e:
                print(e)
                time.sleep(600)
        if(stock_pledge<30):
            resultdata_list[ii] = resultdata_list[ii] + [stock_pledge]
        else:
            resultdata_list.pop(ii)
    write_csvfile(resultfile_path, title, resultdata_list)


def drop_Model_Select():
# 连续多日跌幅模型
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "收盘价连续最低天数", "最低价连续最低天数", "百日位置(%)", "百日最多跌幅天数", "百日最大连续跌幅", "百日最大放量倍数", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(drop_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "收盘价连续最低天数", "最低价连续最低天数", "百日位置(%)", "百日最多跌幅天数", "百日最大连续跌幅", "百日最大放量倍数", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(drop_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = len(stockdata_list)-1
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    modelcounter = 0
    for ii in range(perioddaynum):
        if(float(stockdata_list[ii][9])<0):
            modelcounter += 1
        else:
            break
    volumnratio1 = 1
    for ii in range(modelcounter):
        if(float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])>volumnratio1):
            volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if((modelcounter>3) and (volumnratio1>1.5)):
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        lowerprice = float(stockdata_list[0][5])
        maxprice = max(closingprice_list[:min(100, perioddaynum)])
        minprice = min(closingprice_list[:min(100, perioddaynum)])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        closingcounter = 0
        lowercounter = 0
        for ii in range(1, perioddaynum):
            if(lowerprice<closingprice_list[ii]):
                lowercounter += 1
            else:
                break
        for ii in range(1, perioddaynum):
            if(closingprice<closingprice_list[ii]):
                closingcounter += 1
            else:
                break
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            for jj in range(ii, perioddaynum):
                if(float(stockdata_list[jj][9])<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(tempmodelrange<maxmodelrange):
                        maxmodelrange = tempmodelrange
                    if(tempmodelcounter>maxmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    break
        maxvolumnratio1 = 0
        maxvolumndate1 = stockdata_list[0][0]
        for ii in range(1, min(100, perioddaynum)):
            tempvolumnratio1 = float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
                maxvolumndate1 = stockdata_list[ii][0]
        if((modelrange<maxmodelrange*2/3) and (modelcounter>maxmodelcounter/2)):
            return [stockinfo, stockdata_list[0][9], modelcounter, modelrange, volumnratio1, closingcounter, lowercounter, reboundrange, maxmodelcounter, maxmodelrange, maxvolumnratio1, maxvolumndate1]
    return []


def gap_Model_Select():
# 缺口理论模型
    resultfile_path = os.path.join(resultdata_path, "gap_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跳空数量", "最近跳空天数", "最近跌幅", "总跳空天数", "总跌幅", "最近跳空幅度", "最大跳空幅度", "百日位置(%)"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(gap_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def gap_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "gap_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跳空数量", "最近跳空天数", "最近跌幅", "总跳空天数", "总跌幅", "最近跳空幅度", "最大跳空幅度", "百日位置(%)"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(gap_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def gap_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(200, len(stockdata_list)-1)
    if(perioddaynum<200):
        return []    
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+1]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+1]]
    gapoffset_list = []
    gaprange_list = []
    gapcounter = 0
    for ii in range(1, perioddaynum):
        if(upperprice_list[ii]<lowerprice_list[ii+1]):
            if(max(upperprice_list[:ii+1])<lowerprice_list[ii+1]):
                gapcounter += 1
                gapoffset_list.append(ii)
                gaprange_list.append((upperprice_list[ii]/lowerprice_list[ii+1]-1)*100)
            else:
                break
    if(gapcounter>2):
        modelrange1 = (closingprice/closingprice_list[gapoffset_list[0]]-1)*100
        modelrange2 = (closingprice/closingprice_list[gapoffset_list[-1]]-1)*100
        lowerprice = float(stockdata_list[0][5])
        maxprice = max(closingprice_list[:min(100, perioddaynum)])
        minprice = min(closingprice_list[:min(100, perioddaynum)])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        return [stockinfo, stockdata_list[0][9], gapcounter, gapoffset_list[0], modelrange1, gapoffset_list[-1], modelrange2, gaprange_list[0], min(gaprange_list), reboundrange]
    return []


def rise_Model_Select():
# 连续多日上涨(&阳线)模型
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "收盘价连续最高天数", "最高价连续最高天数", "百日位置(%)", "百日最多涨幅天数", "百日最大连续涨幅", "百日最大放量倍数", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(rise_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def rise_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "收盘价连续最高天数", "最高价连续最高天数", "百日位置(%)", "百日最多涨幅天数", "百日最大连续涨幅", "百日最大放量倍数", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(rise_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def rise_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = len(stockdata_list)-1
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    modelcounter = 0
    for ii in range(perioddaynum):
#        if((float(stockdata_list[ii][9])>0) or (float(stockdata_list[ii][3])>float(stockdata_list[ii][6]))):
#        if(float(stockdata_list[ii][3])>float(stockdata_list[ii][6])):
        if(float(stockdata_list[ii][9])>0):
            modelcounter += 1
        else:
            break
    volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if((modelcounter>3) and (volumnratio1>1)):
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        upperprice = float(stockdata_list[0][4])
        maxprice = max(closingprice_list[:min(100, perioddaynum)])
        minprice = min(closingprice_list[:min(100, perioddaynum)])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        closingcounter = 0
        uppercounter = 0
        for ii in range(1, perioddaynum):
            if(upperprice>closingprice_list[ii]):
                uppercounter += 1
            else:
                break
        for ii in range(1, perioddaynum):
            if(closingprice>closingprice_list[ii]):
                closingcounter += 1
            else:
                break
        maxvolumnratio1 = 0
        maxvolumndate1 = stockdata_list[0][0]
        for ii in range(1, min(100, perioddaynum)):
            tempvolumnratio1 = float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
                maxvolumndate1 = stockdata_list[ii][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            for jj in range(ii, perioddaynum):
                if(float(stockdata_list[jj][9])>0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(tempmodelrange>maxmodelrange):
                        maxmodelrange = tempmodelrange
                    if(tempmodelcounter>maxmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    break
        if((reboundrange<50) and ((volumnratio1/maxvolumnratio1)>0.6)):
            return [stockinfo, stockdata_list[0][9], modelcounter, modelrange, volumnratio1, closingcounter, uppercounter, reboundrange, maxmodelcounter, maxmodelrange, maxvolumnratio1, maxvolumndate1]
    return []


def vshape_Model_Select():
# 放量上涨模型
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "放量倍数", "相对放量倍数", "前一日跌幅", "当日涨幅", "百日最大放量倍数", "日期", "百日最大相对放量倍数", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(vshape_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def vshape_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "放量倍数", "相对放量倍数", "前一日跌幅", "当日涨幅", "百日最大放量倍数", "日期", "百日最大相对放量倍数", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(vshape_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def vshape_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    if((float(stockdata_list[1][3])<float(stockdata_list[1][6])) and ((float(stockdata_list[0][3])>float(stockdata_list[0][6])))
        and (float(stockdata_list[0][5])<float(stockdata_list[1][3])) and (float(stockdata_list[1][9])<-3) and (float(stockdata_list[0][9])>1)
        and ((float(stockdata_list[0][10])/float(stockdata_list[1][10]))>abs(float(stockdata_list[0][9])/float(stockdata_list[1][9])))):
        maxprice = max([float(item[3]) for item in stockdata_list[:100]])
        minprice = min([float(item[3]) for item in stockdata_list[:100]])
        closingprice = float(stockdata_list[0][3])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
        volumnratio2 = abs((float(stockdata_list[0][10])*float(stockdata_list[1][9]))/(float(stockdata_list[1][10])*float(stockdata_list[0][9])))
        maxvolumnratio1 = 0
        maxvolumndate1 = stockdata_list[0][0]
        maxvolumnratio2 = 0
        maxvolumndate2 = stockdata_list[0][0]
        for ii in range(2, min(100,len(stockdata_list)-1)):
            if((float(stockdata_list[ii+1][3])<float(stockdata_list[ii+1][6])) and ((float(stockdata_list[ii][3])>float(stockdata_list[ii][6])))
                and (float(stockdata_list[ii][5])<float(stockdata_list[ii+1][3])) and (float(stockdata_list[ii+1][9])<-3) and (float(stockdata_list[ii][9])>1)
                and ((float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10]))>abs(float(stockdata_list[ii][9])/float(stockdata_list[ii+1][9])))):
                tempvolumnratio1 = float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])
                tempvolumnratio2 = abs((float(stockdata_list[ii][10])*float(stockdata_list[ii+1][9]))/(float(stockdata_list[ii+1][10])*float(stockdata_list[ii][9])))
                if(maxvolumnratio1<tempvolumnratio1):
                    maxvolumnratio1 = tempvolumnratio1
                    maxvolumndate1 = stockdata_list[ii][0]
                if(maxvolumnratio2<tempvolumnratio2):
                    maxvolumnratio2 = tempvolumnratio2
                    maxvolumndate2 = stockdata_list[ii][0]
        if(reboundrange<50):
            return [stockinfo, reboundrange, volumnratio1, volumnratio2, stockdata_list[1][9], stockdata_list[0][9], maxvolumnratio1, maxvolumndate1, maxvolumnratio2, maxvolumndate2]
    return []


def shadow_Model_Select():
# 收下影线金针探底模型
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度", "百日位置(%)", "放量倍数", "百日最大下影线幅度", "日期", "百日最大放量倍数", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(shadow_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度", "百日位置(%)", "放量倍数", "百日最大下影线幅度", "日期", "百日最大放量倍数", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(shadow_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    openrange = (float(stockdata_list[0][6])-float(stockdata_list[0][7]))/float(stockdata_list[0][7])*100
    upperrange = (float(stockdata_list[0][4])-max(float(stockdata_list[0][3]), float(stockdata_list[0][6])))/float(stockdata_list[0][7])*100
    shadowrange = (min(float(stockdata_list[0][3]), float(stockdata_list[0][6]))-float(stockdata_list[0][5]))/float(stockdata_list[0][7])*100
    cylinderrange = (float(stockdata_list[0][3]) - float(stockdata_list[0][6]))/float(stockdata_list[0][7])*100
    volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if((float(stockdata_list[0][9])<3) and (shadowrange>3) and (float(stockdata_list[0][5])<min([float(item[3]) for item in stockdata_list[:30]]))):
        maxprice = max([float(item[3]) for item in stockdata_list[:100]])
        minprice = min([float(item[3]) for item in stockdata_list[:100]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        maxvolumnratio1 = 0
        maxvolumndate1 = stockdata_list[0][0]
        maxshadowrange = 0
        maxshadowdate = stockdata_list[0][0]
        for ii in range(1, min(100,len(stockdata_list)-1)):
            tempvolumnratio1 = float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])
            tempshadowrange = (min(float(stockdata_list[ii][3]), float(stockdata_list[ii][6]))-float(stockdata_list[ii][5]))/float(stockdata_list[ii][7])*100
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
                maxvolumndate1 = stockdata_list[ii][0]
            if(maxshadowrange<tempshadowrange):
                maxshadowrange = tempshadowrange
                maxshadowdate = stockdata_list[ii][0]
        if(reboundrange<50):
            return [stockinfo, stockdata_list[0][9], openrange, cylinderrange, shadowrange, upperrange, reboundrange, volumnratio1, maxshadowrange, maxshadowdate, maxvolumnratio1, maxvolumndate1]
    return []


def parting_Model_Select():
# 分型模型 N=2
    resultfile_path = os.path.join(resultdata_path, "parting_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "下分型回升幅度", "回升天数", "上分型下跌幅度", "下跌天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(parting_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def parting_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "parting_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "下分型回升幅度", "回升天数", "上分型下跌幅度", "下跌天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(parting_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def parting_Model_Select_pipeline(filename):
    N = 2
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-N)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N]]
    maxprice_list = []
    minprice_list = []
    maxoffset_list = []
    minoffset_list = []
    for ii in range(N, perioddaynum-1):
        if((upperprice_list[ii-2]<upperprice_list[ii-1]<upperprice_list[ii]>upperprice_list[ii+1]>upperprice_list[ii+2]) and \
            (lowerprice_list[ii-2]<lowerprice_list[ii-1]<lowerprice_list[ii]>lowerprice_list[ii+1]>lowerprice_list[ii+2]) and \
            (closingprice_list[ii-2]<closingprice_list[ii-1]<closingprice_list[ii]>closingprice_list[ii+1]>closingprice_list[ii+2])):
            maxprice_list.append(upperprice_list[ii])
            maxoffset_list.append(ii)
        if((upperprice_list[ii-2]>upperprice_list[ii-1]>upperprice_list[ii]<upperprice_list[ii+1]<upperprice_list[ii+2]) and \
            (lowerprice_list[ii-2]>lowerprice_list[ii-1]>lowerprice_list[ii]<lowerprice_list[ii+1]<lowerprice_list[ii+2]) and \
            (closingprice_list[ii-2]>closingprice_list[ii-1]>closingprice_list[ii]<closingprice_list[ii+1]<closingprice_list[ii+2])):
            minprice_list.append(lowerprice_list[ii])
            minoffset_list.append(ii)
    if((len(minoffset_list)>3) and (len(maxoffset_list)>3) and (minoffset_list[0]<maxoffset_list[0])):
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        reboundcounter = minoffset_list[0]
        if(reboundrange<20):
            return [stockinfo, stockdata_list[0][9], reboundrange, reboundcounter, failrange, failcounter]
    return []


def RSRS_Model_Select():
# RSRS历史择时模型
    resultfile_path = os.path.join(resultdata_path, "RSRS_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "RSRS因子", "beta分位", "rsquared", "最近多头幅度", "最近多头天数", "最近空头幅度", "最近空头天数", "上一多头幅度", "上一多头天数", "上一空头幅度", "上一空头天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(RSRS_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def RSRS_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "RSRS_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "RSRS因子", "beta分位", "rsquared", "最近多头幅度", "最近多头天数", "最近空头幅度", "最近空头天数", "上一多头幅度", "上一多头天数", "上一空头幅度", "上一空头天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(RSRS_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def RSRS_Model_Select_pipeline(filename):
    N = 16
    P1 = 0.1
    P2 = 0.9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-N)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N]]
    beta_list = [0]*perioddaynum
    betadist_list = [0]*perioddaynum
    rsquared_list = [0]*perioddaynum
    zscore_list = [0]*perioddaynum
    zscoredist_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum)):
        model = sm.OLS(upperprice_list[ii:ii+N], sm.add_constant(lowerprice_list[ii:ii+N]))
        modelfit = model.fit()
        if(len(modelfit.params)==2):
            beta = modelfit.params[1]
            r2 = modelfit.rsquared
        else:
            beta = 0
            r2 = 0
        beta_list[ii] = beta
        rsquared_list[ii] = r2
        zscore_list[ii] = beta*r2
    betasort_list = sorted(beta_list)
    for ii in range(perioddaynum):
        betadist_list[ii] = betasort_list.index(beta_list[ii])/perioddaynum
    zscoresort_list = sorted(zscore_list)
    for ii in range(perioddaynum):
        zscoredist_list[ii] = zscoresort_list.index(zscore_list[ii])/perioddaynum
    minprice_list = []
    minoffset_list = []
    maxprice_list = []
    maxoffset_list = []
    isDrop = True
    for ii in reversed(range(1, perioddaynum)):
        if(isDrop):
            if(zscoredist_list[ii-1]>P2):
                minprice_list.insert(0, closingprice_list[ii])
                minoffset_list.insert(0, ii)
                isDrop=False
        else:
            if(zscoredist_list[ii-1]<P1):
                maxprice_list.insert(0, closingprice_list[ii])
                maxoffset_list.insert(0, ii)
                isDrop=True
    if((len(minprice_list)>3) and (len(maxprice_list)>3) and (not isDrop) and (minoffset_list[0]<maxoffset_list[0]) and (zscoredist_list[0]>P2)):
        reboundcounter = minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        if(reboundrange<20):
            return [stockinfo, stockdata_list[0][9], zscore_list[0], betadist_list[0], rsquared_list[0], reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter]
    return []


def OBV_Model_Select():
# 累计成交量模型
    resultfile_path = os.path.join(resultdata_path, "OBV_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测交叉天数", "OBV下方天数", "上穿前总跌幅", "累计OBV", "30日MAOBV", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(OBV_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def OBV_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "OBV_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测交叉天数", "OBV下方天数", "上穿前总跌幅", "累计OBV", "30日MAOBV", "百日最大下方天数", "百日最大上穿前跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(OBV_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def OBV_Model_Select_pipeline(filename):
    N = 30
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = len(stockdata_list)-N
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    chg_list = [float(item[9]) for item in stockdata_list[:perioddaynum+N]]
    obv_list = [float(item[10]) for item in stockdata_list[:perioddaynum+N]]
    obvsum_list = [0]*(perioddaynum+N+1)
    MA_list = [0]*perioddaynum
    DIFF_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum+N)):
        if(chg_list[ii]>0):
            obvsum_list[ii] = obvsum_list[ii+1] + obv_list[ii]
        elif(chg_list[ii]<0):
            obvsum_list[ii] = obvsum_list[ii+1] - obv_list[ii]
        else:
            obvsum_list[ii] = obvsum_list[ii+1]
    for ii in range(perioddaynum):
        MA_list[ii] = np.mean(obvsum_list[ii:ii+N])
        DIFF_list[ii] = obvsum_list[ii] - MA_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter+=1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, obvsum_list[0], MA_list[0], maxmodelcounter, maxmodelrange]
    return []


def obvper_Model_Select():
# 成交量放大历史择时模型
    resultfile_path = os.path.join(resultdata_path, "obvper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "obv历史分位", "最近放量幅度", "最近放量天数", "最近缩量幅度", "最近缩量天数", "上一放量幅度", "上一放量天数", "上一缩量幅度", "上一缩量天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(obvper_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def obvper_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "obvper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "obv历史分位", "最近放量幅度", "最近放量天数", "最近缩量幅度", "最近缩量天数", "上一放量幅度", "上一放量天数", "上一缩量幅度", "上一缩量天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obvper_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def obvper_Model_Select_pipeline(filename):
    N = 10
    P1 = 0.2
    P2 = 0.8
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-N)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    obv_list = [float(item[10]) for item in stockdata_list[:perioddaynum+N]]
    obvN_list = [0]*perioddaynum
    obvdist_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        obvN_list[ii] = sum(obv_list[ii:ii+N])
    obvsort_list = sorted(obvN_list)
    for ii in range(perioddaynum):
        obvdist_list[ii] = obvsort_list.index(obvN_list[ii])/perioddaynum
    minprice_list = []
    minoffset_list = []
    maxprice_list = []
    maxoffset_list = []
    isDrop = True
    for ii in reversed(range(1, perioddaynum)):
        if(isDrop):
            if(obvdist_list[ii-1]>P2):
                minprice_list.insert(0, closingprice_list[ii])
                minoffset_list.insert(0, ii)
                isDrop=False
        else:
            if(obvdist_list[ii-1]<P1):
                maxprice_list.insert(0, closingprice_list[ii])
                maxoffset_list.insert(0, ii)
                isDrop=True
    if((len(minprice_list)>3) and (len(maxprice_list)>3) and (obvdist_list[0]>P2)):
        reboundcounter = minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        if(reboundrange<20):
            return [stockinfo, stockdata_list[0][9], obvdist_list[0], reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter]
    return []


def obvtrend_Model_Select():
# 成交量放大日线模型
    resultfile_path = os.path.join(resultdata_path, "obvtrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日obv线上穿预测天数", "30日obv线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(obvtrend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def obvtrend_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "obvtrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日obv线上穿预测天数", "30日obv线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obvtrend_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def obvtrend_Model_Select_pipeline(filename):
    N1 = 10
    N2 = 30
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(500, len(stockdata_list)-N2)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
    obv_list = [float(item[10]) for item in stockdata_list[:perioddaynum+N2]]
    MA1_list = [0]*perioddaynum
    MA2_list = [0]*perioddaynum
    DIFF_list = [0]*perioddaynum
    DIFFratio_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        MA1 = np.mean([obv_list[ii:ii+N1]])
        MA2 = np.mean([obv_list[ii:ii+N2]])
        DIFF = MA1-MA2
        MA1_list[ii] = MA1
        MA2_list[ii] = MA2
        DIFF_list[ii] = DIFF
        DIFFratio_list[ii] = DIFF/obv_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        minDIFF = min(DIFF_list[:min(200, perioddaynum)])
        minDIFFdate = stockdata_list[DIFF_list[:min(200, perioddaynum)].index(minDIFF)][0]
        minDIFFratio = min(DIFFratio_list[:min(200, perioddaynum)])
        minDIFFratiodate = stockdata_list[DIFFratio_list[:min(200, perioddaynum)].index(minDIFFratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], maxmodelcounter, maxmodelrange, minDIFF, minDIFFdate, minDIFFratio, minDIFFratiodate]
    return []


def stdper_Model_Select():
# 10日标准差历史择时模型
    resultfile_path = os.path.join(resultdata_path, "stdper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "std历史分位", "最近大波动幅度", "最近大波动天数", "最近小波动幅度", "最近小波动天数", "上一大波动幅度", "上一大波动天数", "上一小波动幅度", "上一小波动天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(stdper_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def stdper_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "stdper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "std历史分位", "最近大波动幅度", "最近大波动天数", "最近小波动幅度", "最近小波动天数", "上一大波动幅度", "上一大波动天数", "上一小波动幅度", "上一小波动天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(stdper_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def stdper_Model_Select_pipeline(filename):
    N = 10
    P1 = 0.2
    P2 = 0.8
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-N)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    std_list = [0]*perioddaynum
    stddist_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        std_list[ii] = np.std(closingprice_list[ii:ii+N])/np.mean(closingprice_list[ii:ii+N])*100
    stdsort_list = sorted(std_list)
    for ii in range(perioddaynum):
        stddist_list[ii] = stdsort_list.index(std_list[ii])/perioddaynum
    minprice_list = []
    minoffset_list = []
    maxprice_list = []
    maxoffset_list = []
    isDrop = True
    for ii in reversed(range(1, perioddaynum)):
        if(isDrop):
            if(stddist_list[ii-1]>P2):
                minprice_list.insert(0, closingprice_list[ii])
                minoffset_list.insert(0, ii)
                isDrop=False
        else:
            if(stddist_list[ii-1]<P1):
                maxprice_list.insert(0, closingprice_list[ii])
                maxoffset_list.insert(0, ii)
                isDrop=True
    if((len(minprice_list)>3) and (len(maxprice_list)>3) and (stddist_list[0]>P2)):
        reboundcounter = minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        if(reboundrange<20):
            return [stockinfo, stockdata_list[0][9], stddist_list[0], reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter]
    return []


def stdtrend_Model_Select():
# 标准差日线模型
    resultfile_path = os.path.join(resultdata_path, "stdtrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日std线上穿预测天数", "30日std线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(stdtrend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def stdtrend_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "stdtrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日std线上穿预测天数", "30日std线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(stdtrend_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def stdtrend_Model_Select_pipeline(filename):
    N1 = 10
    N2 = 30
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(500, len(stockdata_list)-N2)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
    MA1_list = [0]*perioddaynum
    MA2_list = [0]*perioddaynum
    DIFF_list = [0]*perioddaynum
    DIFFratio_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        MA1 = np.std(closingprice_list[ii:ii+N1])/np.mean(closingprice_list[ii:ii+N1])*100
        MA2 = np.std(closingprice_list[ii:ii+N2])/np.mean(closingprice_list[ii:ii+N2])*100
        DIFF = MA1-MA2
        MA1_list[ii] = MA1
        MA2_list[ii] = MA2
        DIFF_list[ii] = DIFF
        DIFFratio_list[ii] = DIFF/closingprice_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        minDIFF = min(DIFF_list[:min(200, perioddaynum)])
        minDIFFdate = stockdata_list[DIFF_list[:min(200, perioddaynum)].index(minDIFF)][0]
        minDIFFratio = min(DIFFratio_list[:min(200, perioddaynum)])
        minDIFFratiodate = stockdata_list[DIFFratio_list[:min(200, perioddaynum)].index(minDIFFratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], maxmodelcounter, maxmodelrange, minDIFF, minDIFFdate, minDIFFratio, minDIFFratiodate]
    return []


def ampper_Model_Select():
# 10日振幅历史择时模型
    resultfile_path = os.path.join(resultdata_path, "ampper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "amp历史分位", "最近大振幅幅度", "最近大振幅天数", "最近小振幅幅度", "最近小振幅天数", "上一大振幅幅度", "上一大振幅天数", "上一小振幅幅度", "上一小振幅天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(ampper_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def ampper_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "ampper_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "amp历史分位", "最近大振幅幅度", "最近大振幅天数", "最近小振幅幅度", "最近小振幅天数", "上一大振幅幅度", "上一大振幅天数", "上一小振幅幅度", "上一小振幅天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(ampper_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def ampper_Model_Select_pipeline(filename):
    N = 10
    P1 = 0.2
    P2 = 0.8
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-N)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N]]
    amp_list = [0]*perioddaynum
    ampdist_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        amp_list[ii] = np.mean([(upperprice_list[jj]-lowerprice_list[jj])/closingprice_list[jj] for jj in range(ii, ii+N)])
    ampsort_list = sorted(amp_list)
    for ii in range(perioddaynum):
        ampdist_list[ii] = ampsort_list.index(amp_list[ii])/perioddaynum
    minprice_list = []
    minoffset_list = []
    maxprice_list = []
    maxoffset_list = []
    isDrop = True
    for ii in reversed(range(1, perioddaynum)):
        if(isDrop):
            if(ampdist_list[ii-1]>P2):
                minprice_list.insert(0, closingprice_list[ii])
                minoffset_list.insert(0, ii)
                isDrop=False
        else:
            if(ampdist_list[ii-1]<P1):
                maxprice_list.insert(0, closingprice_list[ii])
                maxoffset_list.insert(0, ii)
                isDrop=True
    if((len(minprice_list)>3) and (len(maxprice_list)>3) and (ampdist_list[0]>P2)):
        reboundcounter = minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        if(reboundrange<20):
            return [stockinfo, stockdata_list[0][9], ampdist_list[0], reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter]
    return []


def amptrend_Model_Select():
# 振幅日线模型
    resultfile_path = os.path.join(resultdata_path, "amptrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日amp线上穿预测天数", "30日amp线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(amptrend_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def amptrend_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "amptrend_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日amp线上穿预测天数", "30日amp线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(amptrend_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def amptrend_Model_Select_pipeline(filename):
    N1 = 10
    N2 = 30
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(500, len(stockdata_list)-N2)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N2]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N2]]
    MA1_list = [0]*perioddaynum
    MA2_list = [0]*perioddaynum
    DIFF_list = [0]*perioddaynum
    DIFFratio_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        MA1 = np.mean([(upperprice_list[jj]-lowerprice_list[jj])/closingprice_list[jj] for jj in range(ii, ii+N1)])
        MA2 = np.mean([(upperprice_list[jj]-lowerprice_list[jj])/closingprice_list[jj] for jj in range(ii, ii+N2)])
        DIFF = MA1-MA2
        MA1_list[ii] = MA1
        MA2_list[ii] = MA2
        DIFF_list[ii] = DIFF
        DIFFratio_list[ii] = DIFF/closingprice_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        minDIFF = min(DIFF_list[:min(200, perioddaynum)])
        minDIFFdate = stockdata_list[DIFF_list[:min(200, perioddaynum)].index(minDIFF)][0]
        minDIFFratio = min(DIFFratio_list[:min(200, perioddaynum)])
        minDIFFratiodate = stockdata_list[DIFFratio_list[:min(200, perioddaynum)].index(minDIFFratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], maxmodelcounter, maxmodelrange, minDIFF, minDIFFdate, minDIFFratio, minDIFFratiodate]
    return []


def box_Model_Select():
# 箱体模型
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "下跌幅度", "反弹幅度", "反弹比例", "下跌天数", "反弹天数", "回升量比"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(box_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "下跌幅度", "反弹幅度", "反弹比例", "下跌天数", "反弹天数", "回升量比"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(box_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    for paratuple in [(400, 0.3), (300, 0.4), (200, 0.5), (100, 0.6), (60, 0.7), (30, 0.8)]:
        closingprice_list = [float(item[3]) for item in stockdata_list[:min(len(stockdata_list), paratuple[0])]]
        maxprice = max(closingprice_list)
        maxoffset = closingprice_list.index(maxprice)
        minprice = min(closingprice_list)
        minoffset = closingprice_list.index(minprice)
        if((minoffset>2) and (minoffset<maxoffset) and (minprice<paratuple[1]*maxprice)):
            failrange = (minprice-maxprice)/maxprice*100
            reboundrange = (closingprice-minprice)/maxprice*100
            reboundratio = -(reboundrange/failrange)
            amountratio = sum([float(item[10]) for item in stockdata_list[:minoffset]])/sum([float(item[10]) for item in stockdata_list[minoffset:maxoffset]])
            if((reboundrange<abs(failrange)/3) and (minoffset/maxoffset)>1/5):
                return [stockinfo, stockdata_list[0][9], failrange, reboundrange, reboundratio, (maxoffset-minoffset), minoffset, amountratio]
    return []


def wave_Model_Select():
# 波浪模型
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近回升量比", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一回升量比", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "总回升量比", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(wave_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近回升量比", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一回升量比", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "总回升量比", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(wave_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    rounddaynum = 10
    perioddaynum = min(500, len(stockdata_list)-rounddaynum)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum]]
    maxprice_list = []
    minprice_list = []
    maxoffset_list = []
    minoffset_list = []
    lastextremeprice = 0.01
    startoffset = perioddaynum-1
    for ii in range(perioddaynum):
        if(closingprice_list[ii]==min(closingprice_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])):
            minprice_list.append(closingprice_list[ii])
            minoffset_list.append(ii)
            startoffset = ii
            lastextremeprice=closingprice_list[ii]
            isDrop = True
            break
        if(closingprice_list[ii]==max(closingprice_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])):
            return []
    for ii in range(startoffset+1, perioddaynum):
        tempmaxprice = max(closingprice_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])
        tempminprice = min(closingprice_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])
        if(isDrop):
            if((closingprice_list[ii]==tempmaxprice) and ((closingprice_list[ii]-lastextremeprice)/closingprice_list[ii]>0.10)):
                maxprice_list.append(closingprice_list[ii])
                maxoffset_list.append(ii)
                lastextremeprice=closingprice_list[ii]
                isDrop = False
            elif((closingprice_list[ii]==tempminprice) and (closingprice_list[ii]<minprice_list[-1])):
                minprice_list[-1]=closingprice_list[ii]
                minoffset_list[-1]=ii
                lastextremeprice=closingprice_list[ii]
        else:
            if((closingprice_list[ii]==tempminprice) and ((closingprice_list[ii]-lastextremeprice)/closingprice_list[ii]<-0.10)):
                minprice_list.append(closingprice_list[ii])
                minoffset_list.append(ii)
                lastextremeprice=closingprice_list[ii]
                isDrop = True
            elif((closingprice_list[ii]==tempmaxprice) and (closingprice_list[ii]>maxprice_list[-1])):
                maxprice_list[-1]=closingprice_list[ii]
                maxoffset_list[-1]=ii
                lastextremeprice=closingprice_list[ii]
    upwavecounter = 0
    downwavecounter = 0
    for ii in range(len(maxprice_list)-2):
        if(minprice_list[ii]>=minprice_list[ii+1]):
            upwavecounter+=1
        else:
            break
    for ii in range(upwavecounter+1, len(maxprice_list)-1):
        if(maxprice_list[ii]<=maxprice_list[ii+1]):
            downwavecounter+=1
        else:
            break
    if((len(minprice_list)>3) and ((len(maxprice_list)>3))):
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        reboundcounter = minoffset_list[0]
        amountratio = (sum([float(item[10]) for item in stockdata_list[:minoffset_list[0]]]))/sum([float(item[10]) for item in stockdata_list[minoffset_list[0]:maxoffset_list[0]]])
        wavevallratio = (minprice_list[0]/minprice_list[1]-1)*100
        wavepeakratio = (maxprice_list[0]/maxprice_list[1]-1)*100
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastamountratio = sum([float(item[10]) for item in stockdata_list[maxoffset_list[0]:minoffset_list[1]]])/sum([float(item[10]) for item in stockdata_list[minoffset_list[1]:maxoffset_list[1]]])
        lastwavepeakratio = (maxprice_list[1]/maxprice_list[2]-1)*100
        lastwavevallratio = (minprice_list[1]/minprice_list[2]-1)*100
        minprice = minprice_list[upwavecounter]
        maxprice = maxprice_list[upwavecounter+1+downwavecounter]
        sumfailrange = (minprice/maxprice-1)*100
        sumfailcounter = maxoffset_list[upwavecounter+1+downwavecounter] - minoffset_list[upwavecounter]
        sumreboundrange = (closingprice/minprice-1)*100
        sumreboundcounter = minoffset_list[upwavecounter]
        sumamountratio = sum([float(item[10]) for item in stockdata_list[:minoffset_list[upwavecounter]]])/sum([float(item[10]) for item in stockdata_list[minoffset_list[upwavecounter]:maxoffset_list[upwavecounter+1+downwavecounter]]])
        maxfailrange = 0
        maxreboundrange = 0
        maxfailcounter = 0
        maxreboundcounter = 0
        for ii in range(2, len(minprice_list)-1):
            tempfailrange = (minprice_list[ii]/maxprice_list[ii]-1)*100
            tempreboundrange = (maxprice_list[ii]/minprice_list[ii+1]-1)*100
            tempfailcounter = maxoffset_list[ii]-minoffset_list[ii]
            tempreboundcounter = minoffset_list[ii+1]-maxoffset_list[ii]
            if(maxfailrange>tempfailrange):
                maxfailrange = tempfailrange
            if(maxreboundrange<tempreboundrange):
                maxreboundrange = tempreboundrange
            if(maxfailcounter<tempfailcounter):
                maxfailcounter = tempfailcounter
            if(maxreboundcounter<tempreboundcounter):
                maxreboundcounter = tempreboundcounter
        if((failrange<lastfailrange*2/3) and (failcounter>lastfailcounter*2/3) and (reboundrange<abs(failrange)/3) and (reboundcounter>3)):
            return [stockinfo, stockdata_list[0][9], downwavecounter, upwavecounter, reboundrange, reboundcounter, failrange, failcounter, amountratio, wavevallratio, wavepeakratio,
                    lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, lastamountratio, lastwavevallratio, lastwavepeakratio,
                    sumreboundrange, sumreboundcounter, sumfailrange, sumfailcounter, sumamountratio, maxreboundrange, maxreboundcounter, maxfailrange, maxfailcounter]
    return []


def volumn_Model_Select():
# 放量模型
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅", "百日最大放量倍数", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(volumn_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅", "百日最大放量倍数", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(volumn_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if(volumnratio1>2):
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        closingprice = float(stockdata_list[0][3])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        maxvolumnratio1 = 0
        maxvolumndate1 = stockdata_list[0][0]
        for ii in range(2, min(100,len(stockdata_list)-1)):
            tempvolumnratio1 = float(stockdata_list[ii][10])/float(stockdata_list[ii+1][10])
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
                maxvolumndate1 = stockdata_list[ii][0]
        drop5range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        if(reboundrange<50):
            return [stockinfo, stockdata_list[0][9], volumnratio1, reboundrange, drop5range, drop10range, drop30range, maxvolumnratio1, maxvolumndate1]
    return []


def tangle_Model_Select():
# 1-5-10-30-60日线纠缠
    title = ["股票名称", "当日涨跌幅", "百日位置(%)", "日线纠缠幅度", "日线纠缠天数", "日线偏离幅度", "日线偏离天数"]
    resultfile_path = os.path.join(resultdata_path, "tangle_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(tangle_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def tangle_Model_Select_par():
    title = ["股票名称", "当日涨跌幅", "百日位置(%)", "日线纠缠幅度", "日线纠缠天数", "日线偏离幅度", "日线偏离天数"]
    resultfile_path = os.path.join(resultdata_path, "tangle_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(tangle_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def tangle_Model_Select_pipeline(filename):
    N_list = [1, 5, 10, 30, 60]
    P = 0.1
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-max(N_list))
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+max(N_list)]]
    MA_list = [[0]*len(N_list)]*perioddaynum
    div_list = [0]*perioddaynum
    divdist_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        for jj in range(len(N_list)):
            MA_list[ii][jj]=np.mean(closingprice_list[ii:ii+N_list[jj]])
        div_list[ii] = 2*(max(MA_list[ii])-min(MA_list[ii]))/(max(MA_list[ii])+min(MA_list[ii]))
    divsort_list = sorted(div_list)
    for ii in range(perioddaynum):
        divdist_list[ii] = divsort_list.index(div_list[ii])/perioddaynum
    if(divdist_list[0]<P):
        tanglecounter = 1
        for ii in range(1,perioddaynum):
            if(divdist_list[ii]<P):
                tanglecounter+=1
            else:
                break
        tanglerange = (closingprice/closingprice_list[tanglecounter]-1)*100
        divcounter = 0
        for ii in range(tanglecounter, perioddaynum):
            if(divdist_list[ii]<P):
                break
            else:
                divcounter+=1
        divrange = (closingprice_list[tanglecounter]/closingprice_list[tanglecounter+divcounter]-1)*100
        maxprice = max(closingprice_list[:100])
        minprice = min(closingprice_list[:100])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        if(reboundrange<50):
            return [stockinfo, stockdata_list[0][9], reboundrange, tanglerange, tanglecounter, divrange, divcounter]
    return []


def trend_Model_Select():
# K线图 N1日线 贯穿 N2日线
    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend10T30_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend_Model_Select_par():
    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend10T30_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5_Model_Select_pipeline(filename):
    return trend_Model_Select_pipeline(filename,1,5)
def trend1T10_Model_Select_pipeline(filename):
    return trend_Model_Select_pipeline(filename,1,10)
def trend5T10_Model_Select_pipeline(filename):
    return trend_Model_Select_pipeline(filename,5,10)
def trend10T30_Model_Select_pipeline(filename):
    return trend_Model_Select_pipeline(filename,10,30)
def trend_Model_Select_pipeline(filename, N1, N2):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(200, len(stockdata_list)-N2)
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
    MA1_list = [0]*perioddaynum
    MA2_list = [0]*perioddaynum
    DIFF_list = [0]*perioddaynum
    DIFFratio_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        MA1 = np.mean([closingprice_list[ii:ii+N1]])
        MA2 = np.mean([closingprice_list[ii:ii+N2]])
        DIFF = MA1-MA2
        MA1_list[ii] = MA1
        MA2_list[ii] = MA2
        DIFF_list[ii] = DIFF
        DIFFratio_list[ii] = DIFF/closingprice_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
# Solve Function MA1(new)-MA2(new)=DIFF  (i.e. 0, DIFF_list[0], 2DIFF_list[0]-DIFF_list[1])
# (x+sum(closingprice_list[:N1-1]))/N1 - (x+sum(closingprice_list[:N2-1]))/N2 = DIFF 
# x = (DIFF+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        crossprice = (sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        crossrange = (crossprice/closingprice-1)*100
        trendprice = ((2*DIFF_list[0]-DIFF_list[1])+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trendrange = (trendprice/closingprice-1)*100
        parallelprice = (DIFF_list[0]+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallelrange = (parallelprice/closingprice-1)*100
        minDIFF = min(DIFF_list[:min(100, perioddaynum)])
        minDIFFdate = stockdata_list[DIFF_list[:min(100, perioddaynum)].index(minDIFF)][0]
        minDIFFratio = min(DIFFratio_list[:min(100, perioddaynum)])
        minDIFFratiodate = stockdata_list[DIFFratio_list[:min(100, perioddaynum)].index(minDIFFratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDIFF, minDIFFdate, minDIFFratio, minDIFFratiodate]
    return []


def KDJ_Model_Select():
# KDJ 模型 n=9
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低J值", "日期", "百日最高J值", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJ_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低J值", "日期", "百日最高J值", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJ_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_pipeline(filename):
    N = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-N)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N]]
    K_list = [50]*(perioddaynum+1)
    D_list = [50]*(perioddaynum+1)
    J_list = [50]*perioddaynum
    DIFF_list = [0]*perioddaynum
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(perioddaynum)):
        C9 = closingprice_list[ii]
        H9 = max(upperprice_list[ii:ii+N])
        L9 = min(lowerprice_list[ii:ii+N])
        if(H9==L9):
            RSV = 50
        else:
            RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[ii+1]+1/3*RSV
        D = 2/3*D_list[ii+1]+1/3*K
        J = 3*K-2*D
        K_list[ii] = K
        D_list[ii] = D
        J_list[ii] = J
        DIFF_list[ii] = K-D
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        Kprice = (H9-L9)*K_list[0]/100+L9
        Krange = (Kprice/closingprice-1)*100
        modelslope = (DIFF_list[0]-DIFF_list[1])/((K_list[0]+D_list[0])/2)
        maxJ = max(J_list[:min(100, perioddaynum)])
        maxJdate = stockdata_list[J_list.index(maxJ)][0]
        minJ = min(J_list[:min(100, perioddaynum)])
        minJdate = stockdata_list[J_list.index(minJ)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, Krange, K_list[0], D_list[0], J_list[0], RSV, maxmodelcounter, maxmodelrange, minJ, minJdate, maxJ, maxJdate]
    return []


def CCI_Model_Select():
# CCI 模型 n=14
    resultfile_path = os.path.join(resultdata_path, "CCI_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "CCI上涨天数", "CCI上涨幅度", "CCI下跌天数", "CCI下跌幅度", "当日CCI", "百日最大下跌天数", "百日最大下跌幅度", "百日最低CCI值", "日期", "百日最高CCI值", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(CCI_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def CCI_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "CCI_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "CCI上涨天数", "CCI上涨幅度", "CCI下跌天数", "CCI下跌幅度", "当日CCI", "百日最大下跌天数", "百日最大下跌幅度", "百日最低CCI值", "日期", "百日最高CCI值", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(CCI_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def CCI_Model_Select_pipeline(filename):
    N = 14
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-N)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N]]
    TP_list = [0]*(perioddaynum+N)
    MA_list = [0]*perioddaynum
    MD_list = [0]*perioddaynum
    CCI_list = [0]*perioddaynum
    maxprice_list = []
    minprice_list = []
    maxoffset_list = []
    minoffset_list = []
    for ii in range(perioddaynum+N):
        TP_list[ii] = (closingprice_list[ii]+upperprice_list[ii]+lowerprice_list[ii])/3
    for ii in range(perioddaynum):
        MA_list[ii] = np.mean(TP_list[ii:ii+N])
        MD_list[ii] = np.mean(np.abs([TP_list[jj]-MA_list[ii] for jj in range(ii,ii+N)]))
        CCI_list[ii] = (TP_list[ii]-MA_list[ii])/MD_list[ii]/0.015
    for ii in range(1, perioddaynum-1):
        if((CCI_list[ii]>CCI_list[ii-1]) and (CCI_list[ii]>CCI_list[ii+1])):
            maxprice_list.append(closingprice_list[ii])
            maxoffset_list.append(ii)
        if((CCI_list[ii]<CCI_list[ii-1]) and (CCI_list[ii]<CCI_list[ii+1])):
            minprice_list.append(closingprice_list[ii])
            minoffset_list.append(ii)
    if((len(minoffset_list)>3) and (len(maxoffset_list)>3) and (minoffset_list[0]<maxoffset_list[0])):
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        reboundcounter = minoffset_list[0]
        maxCCI = max(CCI_list[:min(100, perioddaynum)])
        maxCCIdate = stockdata_list[CCI_list.index(maxCCI)][0]
        minCCI = min(CCI_list[:min(100, perioddaynum)])
        minCCIdate = stockdata_list[CCI_list.index(minCCI)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(failcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum-1):
                if(CCI_list[jj]<CCI_list[jj+1]):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(failrange<maxmodelrange*2/3):
            return [stockinfo, stockdata_list[0][9], reboundcounter, reboundrange, failcounter, failrange, CCI_list[0], maxmodelcounter, maxmodelrange, minCCI, minCCIdate, maxCCI, maxCCIdate]
    return []


def BOLL_Model_Select():
# BOLL 模型 N1=20 N2=2
    resultfile_path = os.path.join(resultdata_path, "BOLL_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "百日位置", "BOLL极限宽", "BOLL下方天数", "BOLL下方涨跌幅", "上一BOLL下穿上轨天数", "下穿涨跌幅", "上一BOLL上穿下轨天数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(BOLL_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLL_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "BOLL_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "百日位置", "BOLL极限宽", "BOLL下方天数", "BOLL下方涨跌幅", "上一BOLL下穿上轨天数", "下穿涨跌幅", "上一BOLL上穿下轨天数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(BOLL_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLL_Model_Select_pipeline(filename):
    N1 = 20
    N2 = 2
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(200, len(stockdata_list)-N1)
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N1]]
    MA_list = [0]*perioddaynum
    STD_list = [0]*perioddaynum
    WIDTH_list = [0]*perioddaynum
    UP_list = [0]*perioddaynum
    DN_list = [0]*perioddaynum
    for ii in range(perioddaynum):
        MA_list[ii] = np.mean(closingprice_list[ii:ii+N1])
        STD_list[ii] = np.std(closingprice_list[ii:ii+N1])
        UP_list[ii] = MA_list[ii]+STD_list[ii]*N2
        DN_list[ii] = MA_list[ii]-STD_list[ii]*N2
        WIDTH_list[ii] = (UP_list[ii]-DN_list[ii])/MA_list[ii]
    if((closingprice_list[1]<DN_list[1]) or (closingprice_list[0]<DN_list[0])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(closingprice_list[ii]<DN_list[ii]):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        upoffset = 0
        for ii in range(modelcounter, perioddaynum):
            if((closingprice_list[ii]>UP_list[ii]) and (closingprice_list[ii-1]<UP_list[ii-1])):
                upoffset = ii
                break
        uprange = (closingprice/closingprice_list[upoffset]-1)*100
        dnoffset = 0
        for ii in range(modelcounter, perioddaynum):
            if((closingprice_list[ii]<DN_list[ii]) and (closingprice_list[ii-1]>DN_list[ii-1])):
                dnoffset = ii
                break
        dnrange = (closingprice/closingprice_list[dnoffset]-1)*100
        widthrange = (WIDTH_list[0]/WIDTH_list[10]-1)*100
        marange = (MA_list[0]/MA_list[10]-1)*100
        maxprice = max(closingprice_list[:100])
        minprice = min(closingprice_list[:100])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        if(reboundrange<50):
            return [stockinfo, stockdata_list[0][9], reboundrange, WIDTH_list[0], modelcounter, modelrange, upoffset, uprange, dnoffset, dnrange, widthrange, marange]
    return []


def PVI_Model_Select():
# PVI 正交易量模型
    resultfile_path = os.path.join(resultdata_path, "PVI_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "PVI上方天数", "PVI上方涨跌幅", "PVI下方天数", "PVI下方涨跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(PVI_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def PVI_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "PVI_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "PVI上方天数", "PVI上方涨跌幅", "PVI下方天数", "PVI下方涨跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(PVI_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def PVI_Model_Select_pipeline(filename):
    N = 72
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-1)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    obv_list = [float(item[10]) for item in stockdata_list[:perioddaynum+1]]
    PVI_list = [1]*(perioddaynum+1)
    MAPVI_list = [1]*(perioddaynum+1)
    DIFF_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum)):
        if(obv_list[ii]/obv_list[ii+1]>1):
            PVI_list[ii] = PVI_list[ii+1]*(closingprice_list[ii]/closingprice_list[ii+1])
        else:
            PVI_list[ii] = PVI_list[ii+1]
        MAPVI_list[ii] = (N-1)/(N+1)*MAPVI_list[ii+1] + 2/(N+1)*PVI_list[ii]
        DIFF_list[ii] = PVI_list[ii]-MAPVI_list[ii]
    if(DIFF_list[0]>0):
        reboundcounter = 1
        for ii in range(1,perioddaynum):
            if(DIFF_list[ii]>0):
                reboundcounter+=1
            else:
                break
        reboundrange = (closingprice/closingprice_list[reboundcounter]-1)*100
        failcounter = 0
        for ii in range(reboundcounter, perioddaynum):
            if(DIFF_list[ii]>0):
                break
            else:
                failcounter+=1
        failrange = (closingprice_list[reboundcounter]/closingprice_list[reboundcounter+failcounter]-1)*100
        if((failrange<0) and (reboundrange<abs(failrange)/3)):
            return [stockinfo, stockdata_list[0][9], reboundcounter, reboundrange, failcounter, failrange]
    return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFF1_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)

    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFF2_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)

    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFF3_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF1_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])

    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF2_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])

    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF3_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFF1_Model_Select_pipeline(filename):
    return MACDDIFF_Model_Select_pipeline(filename, 12, 26, 9)
def MACDDIFF2_Model_Select_pipeline(filename):
    return MACDDIFF_Model_Select_pipeline(filename, 6, 10, 5)
def MACDDIFF3_Model_Select_pipeline(filename):
    return MACDDIFF_Model_Select_pipeline(filename, 21, 34, 8)
def MACDDIFF_Model_Select_pipeline(filename, N1, N2, N3):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-1)
    if(perioddaynum<200):
        return [], []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    MACD_result = []
    DIFF_result = []
    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para(closingprice_list, N1, N2, N3)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if((MACD_list[ii]<0) or (DIFF_list[ii])<0):
                modelcounter+=1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(MACD_list[0]/(MACD_list[1]-MACD_list[0]))
        modelslope = (MACD_list[0]-MACD_list[1])/closingprice
# Solve Function (DIFF(new)-DEA(new))*2 = MACD (i.e. 0, MACD_list[0], 2*MACD_list[0]-MACD_list[1])
# DIFF(new)-((N3-1)/(N3+1)*DEA_list[0]+2/(N3+1)*DIFF(new)) = MACD/2
# (N3-1)/(N3+1)*(DIFF(new)*DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(EMA1(new)-EMA2(new)-DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0]) = MACD/2
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0] = MACD/2*(N3+1)/(N3-1)
# x =  (MACD/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossprice = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossrange = (crossprice/closingprice-1)*100
        trendprice = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trendrange = (trendprice/closingprice-1)*100
        parallelprice = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallelrange = (parallelprice/closingprice-1)*100
        DEA = min(DEA_list[:modelcounter])
        minDEA = min(DEA_list[:min(100, perioddaynum)])
        minDEAdate = stockdata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][0]
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = stockdata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            MACD_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                modelcounter+=1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        modelslope = (DIFF_list[0]-DIFF_list[1])/closingprice
# Solve Function DIFF(new) = DIFF (i.e. 0, DIFF_list[0], 2*DIFF_list[0]-DIFF_list[1])
# EMA1(new)-EMA2(new) = DIFF
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x) = DIFF
# x = (DIFF+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossprice = ((N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossrange = (crossprice/closingprice-1)*100
        trendprice = ((2*DIFF_list[0]-DIFF_list[1])+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trendrange = (trendprice/closingprice-1)*100
        parallelprice = (DIFF_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallelrange = (parallelprice/closingprice-1)*100
        DEA = min(DEA_list[:modelcounter])
        minDEA = min(DEA_list[:min(100, perioddaynum)])
        minDEAdate = stockdata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][0]
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = stockdata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            DIFF_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
    return MACD_result, DIFF_result
def get_MACD_para(price_list, N1, N2, N3):
    perioddaynum = len(price_list)-1
    EMA1_list = [0]*(perioddaynum+1)
    EMA2_list = [0]*(perioddaynum+1)
    DEA_list = [0]*(perioddaynum+1)
    DIFF_list = [0]*perioddaynum
    DEAratio_list = [0]*perioddaynum
    MACD_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum)):
        EMA1 = (N1-1)/(N1+1)*EMA1_list[ii+1] + 2/(N1+1)*price_list[ii]
        EMA2= (N2-1)/(N2+1)*EMA2_list[ii+1] + 2/(N2+1)*price_list[ii]
        DIFF = EMA1 - EMA2
        DEA = (N3-1)/(N3+1)*DEA_list[ii+1] + 2/(N3+1)*DIFF
        DEAratio = DEA/price_list[ii]
        MACD = (DIFF-DEA)*2
        EMA1_list[ii] = EMA1
        EMA2_list[ii] = EMA2
        DIFF_list[ii] = DIFF
        DEA_list[ii] = DEA
        DEAratio_list[ii] = DEAratio
        MACD_list[ii] = MACD
    return EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list


def EMV_Model_Select():
# EMV 模型 (40,16) & 移动平均 EMVDIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "EMVDIFF_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "EMV_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算EMVDIFF金叉天数", "EMVDIFF下方天数", "上穿前总跌幅", "EMV斜率", "EMV", "EMV比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV斜率", "EMV","EMV比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        EMVMACD_result, EMV_result = EMV_Model_Select_pipeline(filename)
        resultdata_list1.append(EMVMACD_result)
        resultdata_list2.append(EMV_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def EMV_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "EMVDIFF_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "EMV_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算EMVDIFF金叉天数", "EMVDIFF下方天数", "上穿前总跌幅", "EMV斜率", "EMV", "EMV比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV斜率", "EMV","EMV比例", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EMV_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def EMV_Model_Select_pipeline(filename):
    N1 = 40
    N2 = 16
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-1)
    if(perioddaynum<300):
        return [], []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+1]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+1]]
    obv_list = [float(item[10]) for item in stockdata_list[:perioddaynum+1]]
    EMV_result = []
    EMVMACD_result = []
    EMV_list = [0]*(perioddaynum+1)
    MAEMV_list = [0]*(perioddaynum+1)
    EMVDIFF_list = [0]*perioddaynum
    EMVratio_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum)):
        MID = (closingprice_list[ii]+upperprice_list[ii]+lowerprice_list[ii])/3 - (closingprice_list[ii+1]+upperprice_list[ii+1]+lowerprice_list[ii+1])/3
        BRO = upperprice_list[ii]-lowerprice_list[ii]
        EM = MID*BRO/obv_list[ii]
        EMV = EMV_list[ii+1]*(N1-1)/(N1+1) + EM*2/(N1+1)
        EMVratio = EMV*obv_list[ii]/(closingprice_list[ii]**2)
        MAEMV = MAEMV_list[ii+1]*(N2-1)/(N2+1) + EMV*2/(N2+1)
        EMVDIFF = EMV-MAEMV
        EMV_list[ii] = EMV
        EMVratio_list[ii] = EMVratio
        MAEMV_list[ii] = MAEMV
        EMVDIFF_list[ii] = EMVDIFF
    if((EMV_list[0]<0) and (EMVDIFF_list[1]<0) and (EMVDIFF_list[0]>EMVDIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(EMVDIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(EMVDIFF_list[0]/(EMVDIFF_list[1]-EMVDIFF_list[0]))
        modelslope = (EMV_list[0]-EMV_list[1])*obv_list[0]/(closingprice**2)
        minEMV = min(EMV_list[:min(100, perioddaynum)])
        minEMVdate = stockdata_list[EMV_list[:min(100, perioddaynum)].index(minEMV)][0]
        minEMVratio = min(EMVratio_list[:min(100, perioddaynum)])
        minEMVratiodate = stockdata_list[EMVratio_list[:min(100, perioddaynum)].index(minEMVratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(EMVDIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            EMVMACD_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, EMV_list[0], EMVratio_list[0], maxmodelcounter, maxmodelrange, minEMV, minEMVdate, minEMVratio, minEMVratiodate]
    if((EMV_list[1]<0) and (EMV_list[0]>EMV_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(EMV_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(EMV_list[0]/(EMV_list[1]-EMV_list[0]))
        modelslope = (EMV_list[0]-EMV_list[1])*obv_list[0]/(closingprice**2)
        minEMV = min(EMV_list[:min(100, perioddaynum)])
        minEMVdate = stockdata_list[EMV_list[:min(100, perioddaynum)].index(minEMV)][0]
        minEMVratio = min(EMVratio_list[:min(100, perioddaynum)])
        minEMVratiodate = stockdata_list[EMVratio_list.index(minEMVratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(200, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(EMV_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            EMV_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, EMV_list[0], EMVratio_list[0], maxmodelcounter, maxmodelrange, minEMV, minEMVdate, minEMVratio, minEMVratiodate]
    return EMVMACD_result, EMV_result


def DMI_Model_Select():
# DMI 模型 & ADX 模型 & ATR 模型
    resultfile_path1 = os.path.join(resultdata_path, "DMI_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "ADX_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "DMI斜率", "PDI", "MDI", "ADX", "百日最大下方天数", "百日最大上穿前跌幅"]
    title2 = ["股票名称", "当日涨跌幅", "ADX趋势天数", "趋势涨跌幅", "DMI斜率", "PDI", "MDI", "ADX", "百日最大趋势天数", "百日最大趋势幅度"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        DMI_result, ADX_result = DMI_Model_Select_pipeline(filename)
        resultdata_list1.append(DMI_result)
        resultdata_list2.append(ADX_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def DMI_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "DMI_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "ADX_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "DMI斜率", "PDI", "MDI", "百日最大下方天数", "百日最大上穿前跌幅"]
    title2 = ["股票名称", "当日涨跌幅", "ADX趋势天数", "趋势涨跌幅", "DMI斜率", "PDI", "MDI", "ADX", "百日最大趋势天数", "百日最大趋势幅度"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(DMI_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def DMI_Model_Select_pipeline(filename):
    N1 = 14
    N2 = 6
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(1000, len(stockdata_list)-N1-1)
    if(perioddaynum<200):
        return [], []
    closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N1+1]]
    upperprice_list = [float(item[4]) for item in stockdata_list[:perioddaynum+N1+1]]
    lowerprice_list = [float(item[5]) for item in stockdata_list[:perioddaynum+N1+1]]
    DMI_result = []
    ADX_result = []
    PDM_list = [0]*(perioddaynum+N1)
    MDM_list = [0]*(perioddaynum+N1)
    TR_list = [0]*(perioddaynum+N1)
    DX_list = [0]*perioddaynum
    PDI_list = [0]*perioddaynum
    MDI_list = [0]*perioddaynum
    DMI_list = [0]*perioddaynum
    MADX_list = [0]*perioddaynum
    for ii in range(perioddaynum+N1):
        TR = max(abs(upperprice_list[ii]-lowerprice_list[ii]), abs(upperprice_list[ii]-closingprice_list[ii+1]), abs(closingprice_list[ii+1]-lowerprice_list[5]))
        PDM = max((upperprice_list[ii]-upperprice_list[ii+1]), 0)
        MDM = max((lowerprice_list[ii+1]-lowerprice_list[ii]), 0)
        if(PDM>MDM):
            MDM = 0
        elif(MDM>PDM):
            PDM = 0
        else:
            MDM = 0
            PDM = 0
        PDM_list[ii] = PDM
        MDM_list[ii] = MDM
        TR_list[ii] = TR
    for ii in reversed(range(perioddaynum)):
        PDM = sum(PDM_list[ii:ii+N1])
        MDM = sum(MDM_list[ii:ii+N1])
        TR = sum(TR_list[ii:ii+N1])
        PDI = (PDM/TR)*100
        MDI = (MDM/TR)*100
        DMI = PDI - MDI
        DX = abs(PDI-MDI)/(PDI+MDI)*100
        MADX = np.mean(DX_list[ii:ii+N2])
        PDI_list[ii] = PDI
        MDI_list[ii] = MDI
        DMI_list[ii] = DMI
        DX_list[ii] = DX
        MADX_list[ii] = MADX
    if((DMI_list[1]<0) and (DMI_list[0]>DMI_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(DMI_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelpredict = math.ceil(DMI_list[0]/(DMI_list[1]-DMI_list[0]))
        modelslope = (DMI_list[0]-DMI_list[1])
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(DMI_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            DMI_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, PDI_list[0], MDI_list[0], MADX_list[0], maxmodelcounter, maxmodelrange]
    if((MADX_list[1]<MADX_list[2]) and (MADX_list[1]<MADX_list[0])):
        modelcounter = 1
        for ii in range(1, perioddaynum-1):
            if(MADX_list[ii]<MADX_list[ii+1]):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelslope = (DMI_list[0]-DMI_list[1])
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum-1):
                if(MADX_list[jj]<MADX_list[jj+1]):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            ADX_result = [stockinfo, stockdata_list[0][9], modelcounter, modelrange, modelslope, PDI_list[0], MDI_list[0], MADX_list[0], maxmodelcounter, maxmodelrange]
    if((MADX_list[1]>MADX_list[2]) and (MADX_list[1]>MADX_list[0])):
        modelcounter = 1
        for ii in range(1, perioddaynum-1):
            if(MADX_list[ii]>MADX_list[ii+1]):
                modelcounter += 1
            else:
                break
        modelrange = (closingprice/closingprice_list[modelcounter]-1)*100
        modelslope = (DMI_list[0]-DMI_list[1])
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum-1):
                if(MADX_list[jj]>MADX_list[jj+1]):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (closingprice_list[ii]/closingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            ADX_result = [stockinfo, stockdata_list[0][9], modelcounter, modelrange, modelslope, PDI_list[0], MDI_list[0], MADX_list[0], maxmodelcounter, maxmodelrange]
    return DMI_result, ADX_result


def obvMACD_Model_Select():
# OBV模型+多空净额比率法修正+MACD 模型 & DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "obvMACD斜率", "百日最大下方天数", "百日最大上穿前跌幅", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "obvDIFF斜率", "百日最大下方天数", "百日最大上穿前跌幅", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        OBVMACD_result, OBVDIFF_result = obvMACD_Model_Select_pipeline(filename)
        resultdata_list1.append(OBVMACD_result)
        resultdata_list2.append(OBVDIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def obvMACD_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "obvMACD斜率", "百日最大下方天数", "百日最大上穿前跌幅", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "obvDIFF斜率", "百日最大下方天数", "百日最大上穿前跌幅", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obvMACD_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def obvMACD_Model_Select_pipeline(filename):
    N1 = 12
    N2 = 26
    N3 = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-1)
    if(perioddaynum<200):
        return [], []
    OBV_list = [float(item[10]) for item in stockdata_list[:perioddaynum+1]]
    OBVMACD_result = []
    OBVDIFF_result = []
    OBVEMA1_list = [0]*(perioddaynum+1)
    OBVEMA2_list = [0]*(perioddaynum+1)
    OBVDEA_list = [0]*(perioddaynum+1)
    OBVDIFF_list = [0]*perioddaynum
    OBVDEAratio_list = [0]*perioddaynum
    OBVMACD_list = [0]*perioddaynum
    for ii in reversed(range(perioddaynum)):
        OBVEMA1 = (N1-1)/(N1+1)*OBVEMA1_list[ii+1] + 2/(N1+1)*OBV_list[ii]
        OBVEMA2 = (N2-1)/(N2+1)*OBVEMA2_list[ii+1] + 2/(N2+1)*OBV_list[ii]
        OBVDIFF = OBVEMA1 - OBVEMA2
        OBVDEA = (N3-1)/(N3+1)*OBVDEA_list[ii+1] + 2/(N3+1)*OBVDIFF
        OBVDEAratio = OBVDEA/OBV_list[ii]
        OBVMACD = (OBVDIFF-OBVDEA)*2
        OBVEMA1_list[ii] = OBVEMA1
        OBVEMA2_list[ii] = OBVEMA2
        OBVDIFF_list[ii] = OBVDIFF
        OBVDEA_list[ii] = OBVDEA
        OBVDEAratio_list[ii] = OBVDEAratio
        OBVMACD_list[ii] = OBVMACD
    if((OBVMACD_list[1]<0) and (OBVMACD_list[0]>OBVMACD_list[1]) and (OBVDEA_list[1]<0)):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(OBVMACD_list[ii]<0):
                modelcounter+=1
            else:
                break
        modelrange = (closingprice/float(stockdata_list[modelcounter][3])-1)*100
        modelpredict = math.ceil(OBVMACD_list[0]/(OBVMACD_list[1]-OBVMACD_list[0]))
        modelslope = (OBVMACD_list[0]-OBVMACD_list[1])/OBV_list[0]
        OBVDEAratio = min(OBVDEAratio_list[:modelcounter])
        minOBVDEAratio = min(OBVDEAratio_list[:min(100, perioddaynum)])
        minOBVDEAratiodate = stockdata_list[OBVDEAratio_list[:min(100, perioddaynum)].index(minOBVDEAratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(OBVMACD_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (float(stockdata_list[ii][3])/float(stockdata_list[ii+tempmodelcounter][3])-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            OBVMACD_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, maxmodelcounter, maxmodelrange, OBVDEAratio, minOBVDEAratio, minOBVDEAratiodate]
    if((OBVDIFF_list[1]<0) and (OBVDIFF_list[0]>OBVDIFF_list[1])):
        modelcounter = 1
        for ii in range(1, perioddaynum):
            if(OBVDIFF_list[ii]<0):
                modelcounter+=1
            else:
                break
        modelrange = (closingprice/float(stockdata_list[modelcounter][3])-1)*100
        modelpredict = math.ceil(OBVDIFF_list[0]/(OBVDIFF_list[1]-OBVDIFF_list[0]))
        modelslope = (OBVDIFF_list[0]-OBVDIFF_list[1])/OBV_list[0]
        OBVDEAratio = min(OBVDEAratio_list[:modelcounter])
        minOBVDEAratio = min(OBVDEAratio_list[:min(100, perioddaynum)])
        minOBVDEAratiodate = stockdata_list[OBVDEAratio_list[:min(100, perioddaynum)].index(minOBVDEAratio)][0]
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, min(100, perioddaynum)):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, perioddaynum):
                if(OBVDIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (float(stockdata_list[ii][3])/float(stockdata_list[ii+tempmodelcounter][3])-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            OBVDIFF_result = [stockinfo, stockdata_list[0][9], modelpredict, modelcounter, modelrange, modelslope, maxmodelcounter, maxmodelrange, OBVDEAratio, minOBVDEAratio, minOBVDEAratiodate]
    return OBVMACD_result, OBVDIFF_result


def lagging_calc(comdata_list, perioddaynum):
    perioddaynum = min(perioddaynum, len(comdata_list)-1)
    laggingcounter = 0
    for ii in range(perioddaynum):
        if(float(comdata_list[ii][2])<float(comdata_list[ii][4])):
            laggingcounter += 1
    laggingrange = (float(comdata_list[0][3])-float(comdata_list[perioddaynum][3]))/float(comdata_list[perioddaynum][3])*100 - (float(comdata_list[0][1])-float(comdata_list[perioddaynum][1]))/float(comdata_list[perioddaynum][1])*100
    return laggingcounter, laggingrange


def lagging_Model_Select():
# 与指数 相比滞后幅度
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "总股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(lagging_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "总股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(lagging_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_pipeline(filename):
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    stockinfo = filename.split(".")[0]
    if(stockinfo.split('_')[-1][0]=="0"):
        indexfile = indexfile_list[0]
    else:
        indexfile = indexfile_list[1]
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    _, indexdata_list = read_csvfile(indexfile)
    offset1 = 0
    offset2 = 0
    comdata_list = []
    while(True):
        if(stockdata_list[offset1][0]>indexdata_list[offset2][0]):
            comdata_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], indexdata_list[offset2][3], 0, float(stockdata_list[offset1][3])/float(indexdata_list[offset2][3])])
            offset1+=1
        elif(stockdata_list[offset1][0]<indexdata_list[offset2][0]):
            comdata_list.append([indexdata_list[offset2][0], stockdata_list[offset1][3], 0, indexdata_list[offset2][3], indexdata_list[offset2][9], float(stockdata_list[offset1][3])/float(indexdata_list[offset2][3])])
            offset2+=1
        else:
            comdata_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], indexdata_list[offset2][3], indexdata_list[offset2][9], float(stockdata_list[offset1][3])/float(indexdata_list[offset2][3])])
            offset1+=1
            offset2+=1
        if(offset1==min(510,len(stockdata_list))):
            break
        if(offset2==min(510,len(indexdata_list))):
            break
    N1 = 12
    N2 = 26
    N3 = 9
    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para([item[5] for item in comdata_list], N1, N2, N3)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        laggingcounter = 0
        for ii in range(len(MACD_list)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                laggingcounter += 1
            else:
                break
        stockrange = (float(comdata_list[0][1])/float(comdata_list[laggingcounter][1])-1)*100
        comrange = (float(comdata_list[0][3])/float(comdata_list[laggingcounter][3])-1)*100
        laggingrange = comrange - stockrange
        lagging30counter, lagging30range = lagging_calc(comdata_list, 30)
        lagging60counter, lagging60range = lagging_calc(comdata_list, 60)
        lagging100counter, lagging100range = lagging_calc(comdata_list, 100)
        lagging200counter, lagging200range = lagging_calc(comdata_list, 200)
        lagging500counter, lagging500range = lagging_calc(comdata_list, 500)
        maxlaggingcounter = 0
        maxlaggingrange = 0
        for ii in range(laggingcounter, min(100, len(comdata_list)-1)):
            templaggingcounter = 0
            templaggingrange = 0
            for jj in range(ii, min(200, len(comdata_list)-1)):
                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                    templaggingcounter += 1
                else:
                    break
                templaggingrange = (float(comdata_list[ii][3])/float(comdata_list[ii+templaggingcounter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templaggingcounter][1])-1)*100
                if(maxlaggingrange<templaggingrange):
                    maxlaggingrange=templaggingrange
                if(maxlaggingcounter<templaggingcounter):
                    maxlaggingcounter=templaggingcounter
        if((laggingcounter>maxlaggingcounter/2) and (laggingrange>maxlaggingrange*2/3)):
            return [stockinfo, comdata_list[0][2], stockrange, comrange, laggingrange, laggingcounter, maxlaggingrange, maxlaggingcounter, lagging30range, lagging30counter, lagging60range, lagging60counter, lagging100range, lagging100counter, lagging200range, lagging200counter, lagging500range, lagging500counter]
    return []
    

def AHCom_Model_Select():
# A股&H股 相比滞后幅度
    AHfile_path = os.path.join(HKdata_path, end_time+".csv")

    def get_AHdata():
        AH_url = "http://quotes.money.163.com/hs/realtimedata/service/ah.php?host=/hs/realtimedata/service/ah.php&page=0&fields=SCHIDESP,PRICE,SYMBOL,AH,PERCENT,VOLUME&count=500"
        AHCom_title = ["A股名称", "A股代码", "A股查询代码", "A股价格", "A股涨跌幅", "H股代码", "H股名称", "H股价格", "H股涨跌幅", "H股溢价率(溢价率=(H股价格*汇率-A股价格)/A股价格*100%)"]
        AHCom_list = []
        response = get_htmltext(AH_url)
        if(response!=""):
            for AHitem in json.loads(response)["list"]:
                if(("ST" in str(AHitem["AH"]["ASTOCKNAME"])) or (float(AHitem["PRICE"])==0) or ("300"==str(AHitem["AH"]["A_SYMBOL"]).zfill(6)[:3])):
                    continue
                AHComitem = [str(AHitem["AH"]["ASTOCKNAME"]), str(AHitem["AH"]["A_SYMBOL"]).zfill(6), str(AHitem["AH"]["ASTOCKCODE"]).zfill(7),
                    str(AHitem["AH"]["A_PRICE"]), str(AHitem["AH"]["A_PERCENT"]*100), str(AHitem["SYMBOL"]).zfill(5), str(AHitem["SCHIDESP"]), 
                    str(AHitem["PRICE"]), str(AHitem["PERCENT"]*100), str(AHitem["AH"]["PREMIUMRATE"])]
                AHCom_list.append(AHComitem)
            for ii in reversed(range(len(AHCom_list))):
                stockHcode = str(AHCom_list[ii][5]).zfill(5)
                stockHinfo = str(AHCom_list[ii][0]) + '_' + str(AHCom_list[ii][5]).zfill(5) + '_' + str(AHCom_list[ii][2]).zfill(7)
                HKfilename = os.path.join(HKdata_path,  stockHinfo+".csv")
                if(not get_YahooHKdata(stockHcode, start_time, end_time, HKfilename)):
                    AHCom_list.pop(ii)
            write_csvfile(os.path.join(AHfile_path), AHCom_title, AHCom_list)
            return True
        return False

    resultfile_path = os.path.join(resultdata_path, "AHCom_Model_Select_Result.csv")
    title = ["股票名称", "股票溢价率", "A股总涨跌幅", "H股总涨跌幅", "总滞后幅", "总滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    if(get_AHdata()):
        _, AHCom_list = read_csvfile(AHfile_path)
        for AHComitem in AHCom_list:
            stockHinfo = str(AHComitem[0]) + '_' + str(AHComitem[5]).zfill(5) + '_' + str(AHComitem[2]).zfill(7)
            HKfilename = os.path.join(HKdata_path,  stockHinfo+".csv")
            A_Hratio = (1/(1+float(AHComitem[9]))-1)*100
            for filename in os.listdir(stockdata_path):
                if(str(AHComitem[2]).zfill(7)==filename.split(".")[0][-7:]):
                    _, HKdata_list = read_csvfile(HKfilename)
                    _, CNdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    stockinfo = filename.split(".")[0]
                    offset1 = 0
                    offset2 = 0
                    comdata_list = []
                    while(True):
                        if(CNdata_list[offset1][0]>HKdata_list[offset2][0]):
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], HKdata_list[offset2][5], 0, float(CNdata_list[offset1][3])/float(HKdata_list[offset2][5])])
                            offset1+=1
                        elif(CNdata_list[offset1][0]<HKdata_list[offset2][0]):
                            comdata_list.append([HKdata_list[offset2][0], CNdata_list[offset1][3], 0, HKdata_list[offset2][5], HKdata_list[offset2][7], float(CNdata_list[offset1][3])/float(HKdata_list[offset2][5])])
                            offset2+=1
                        else:
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], HKdata_list[offset2][5], HKdata_list[offset2][7], float(CNdata_list[offset1][3])/float(HKdata_list[offset2][5])])
                            offset1+=1
                            offset2+=1
                        if(offset1==min(510,len(CNdata_list))):
                            break
                        if(offset2==min(510,len(HKdata_list))):
                            break
                    N1 = 12
                    N2 = 26
                    N3 = 9
                    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para([item[5] for item in comdata_list], N1, N2, N3)
                    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
                        laggingcounter = 0
                        for ii in range(len(MACD_list)):
                            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                                laggingcounter += 1
                            else:
                                break
                        stockrange = (float(comdata_list[0][1])-float(comdata_list[laggingcounter][1]))/float(comdata_list[laggingcounter][1])*100
                        comrange = (float(comdata_list[0][3])-float(comdata_list[laggingcounter][3]))/float(comdata_list[laggingcounter][3])*100
                        laggingrange = comrange - stockrange
                        lagging30counter, lagging30range = lagging_calc(comdata_list, 30)
                        lagging60counter, lagging60range = lagging_calc(comdata_list, 60)
                        lagging100counter, lagging100range = lagging_calc(comdata_list, 100)
                        lagging200counter, lagging200range = lagging_calc(comdata_list, 200)
                        lagging500counter, lagging500range = lagging_calc(comdata_list, 500)
                        maxlaggingcounter = 0
                        maxlaggingrange = 0
                        for ii in range(laggingcounter, min(200, len(comdata_list)-1)):
                            templaggingcounter = 0
                            templaggingrange = 0
                            for jj in range(ii, len(comdata_list)-1):
                                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                                    templaggingcounter += 1
                                else:
                                    break
                                templaggingrange = (float(comdata_list[ii][3])/float(comdata_list[ii+templaggingcounter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templaggingcounter][1])-1)*100
                                if(maxlaggingrange<templaggingrange):
                                    maxlaggingrange=templaggingrange
                                if(maxlaggingcounter<templaggingcounter):
                                    maxlaggingcounter=templaggingcounter
                        if((laggingcounter>maxlaggingcounter/2) and (laggingrange>maxlaggingrange*2/3) and (A_Hratio<50)):
                            resultdata_list.append([stockinfo, A_Hratio, stockrange, comrange, laggingrange, laggingcounter, maxlaggingrange, maxlaggingcounter, lagging30range, lagging30counter, lagging60range, lagging60counter, lagging100range, lagging100counter, lagging200range, lagging200counter, lagging500range, lagging500counter])
                    break
        write_csvfile(resultfile_path, title, resultdata_list)


def ABCom_Model_Select():
# A股&B股 相比滞后幅度
    ABfile_path = os.path.join(Bdata_path , end_time+".csv")

    def get_ABdata():
        AB_url = "http://quotes.money.163.com/hs/realtimedata/service/ab.php?host=/hs/realtimedata/service/ab.php&page=0&query=AB:_exists_;VOLUME:_exists_&fields=NAME,PRICE,SYMBOL,AB,PERCENT,VOLUME,CODE&sort=AB.A_PERCENT&order=desc&count=500&type=query"
        ABCom_title = ["A股名称", "A股代码", "A股查询代码", "A股价格", "A股涨跌幅", "B股代码", "B股查询代码", "B股名称", "B股价格", "B股涨跌幅", "B/A成交量比", "B股溢价率(溢价率=(B股价格*0.8545-A股价格)/A股价格*100%)"]
        ABCom_list = []
        response = get_htmltext(AB_url)
        if(response!=""):
            for ABitem in json.loads(response)["list"]:
                if(("ST" in str(ABitem["AB"]["A_NAME"])) or ("300"==str(ABitem["AB"]["A_SYMBOL"]).zfill(6)[:3])):
                    continue
                ABComitem = [str(ABitem["AB"]["A_NAME"]), str(ABitem["AB"]["A_SYMBOL"]).zfill(6), str(ABitem["AB"]["A_CODE"]).zfill(7),
                    str(ABitem["AB"]["A_PRICE"]), str(ABitem["AB"]["A_PERCENT"]*100), str(ABitem["SYMBOL"]).zfill(6), str(ABitem["CODE"]).zfill(7),
                    str(ABitem["NAME"]), str(ABitem["PRICE"]), str(ABitem["PERCENT"]*100), str(ABitem["AB"]["VOL_RATIO"]), str(ABitem["AB"]["YJL"])]
                ABCom_list.append(ABComitem)
            for ii in reversed(range(len(ABCom_list))):
                stockBcode = str(ABCom_list[ii][6]).zfill(7)
                stockBinfo = str(ABCom_list[ii][0]) + '_' + stockBcode + '_' + str(ABCom_list[ii][2]).zfill(7)
                Bfilename = os.path.join(Bdata_path,  stockBinfo+".csv")
                if(not get_163data(stockBcode, start_time, end_time, Bfilename)):
                    ABCom_list.pop(ii)
            write_csvfile(os.path.join(ABfile_path), ABCom_title, ABCom_list)
            return True
        else:
            return False

    resultfile_path = os.path.join(resultdata_path, "ABCom_Model_Select_Result.csv")
    title = ["股票名称", "股票溢价率", "A股总涨跌幅", "B股总涨跌幅", "总滞后幅", "总滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    if(get_ABdata()):
        _, ABCom_list = read_csvfile(ABfile_path)
        for ABComitem in ABCom_list:
            stockBcode = str(ABComitem[6]).zfill(7)
            stockBinfo = str(ABComitem[0]) + '_' + stockBcode + '_' + str(ABComitem[2]).zfill(7)
            Bfilename = os.path.join(Bdata_path,  stockBinfo+".csv")
            A_Bratio = (1/(1+float(ABComitem[11]))-1)*100
            for filename in os.listdir(stockdata_path):
                if(str(ABComitem[2]).zfill(7)==filename.split(".")[0][-7:]):
                    _, Bdata_list = read_csvfile(Bfilename)
                    _, CNdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    stockinfo = filename.split(".")[0]
                    offset1 = 0
                    offset2 = 0
                    comdata_list = []
                    while(True):
                        if(CNdata_list[offset1][0]>Bdata_list[offset2][0]):
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], Bdata_list[offset2][3], 0, float(CNdata_list[offset1][3])/float(Bdata_list[offset2][3])])
                            offset1+=1
                        elif(CNdata_list[offset1][0]<Bdata_list[offset2][0]):
                            comdata_list.append([Bdata_list[offset2][0], CNdata_list[offset1][3], 0, Bdata_list[offset2][3], Bdata_list[offset2][9], float(CNdata_list[offset1][3])/float(Bdata_list[offset2][3])])
                            offset2+=1
                        else:
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], Bdata_list[offset2][3], Bdata_list[offset2][9], float(CNdata_list[offset1][3])/float(Bdata_list[offset2][3])])
                            offset1+=1
                            offset2+=1
                        if(offset1==min(510, len(CNdata_list))):
                            break
                        if(offset2==min(510, len(Bdata_list))):
                            break
                    N1 = 12
                    N2 = 26
                    N3 = 9
                    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para([item[5] for item in comdata_list], N1, N2, N3)
                    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
                        laggingcounter = 0
                        for ii in range(len(MACD_list)):
                            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                                laggingcounter += 1
                            else:
                                break
                        stockrange = (float(comdata_list[0][1])-float(comdata_list[laggingcounter][1]))/float(comdata_list[laggingcounter][1])*100
                        comrange = (float(comdata_list[0][3])-float(comdata_list[laggingcounter][3]))/float(comdata_list[laggingcounter][3])*100
                        laggingrange = comrange - stockrange 
                        lagging30counter, lagging30range = lagging_calc(comdata_list, 30)
                        lagging60counter, lagging60range = lagging_calc(comdata_list, 60)
                        lagging100counter, lagging100range = lagging_calc(comdata_list, 100)
                        lagging200counter, lagging200range = lagging_calc(comdata_list, 200)
                        lagging500counter, lagging500range = lagging_calc(comdata_list, 500)
                        maxlaggingcounter = 0
                        maxlaggingrange = 0
                        for ii in range(laggingcounter, min(100, len(comdata_list)-1)):
                            templaggingcounter = 0
                            templaggingrange = 0
                            for jj in range(ii, len(comdata_list)-1):
                                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                                    templaggingcounter += 1
                                else:
                                    break
                                templaggingrange = (float(comdata_list[ii][3])/float(comdata_list[ii+templaggingcounter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templaggingcounter][1])-1)*100
                                if(maxlaggingrange<templaggingrange):
                                    maxlaggingrange=templaggingrange
                                if(maxlaggingcounter<templaggingcounter):
                                    maxlaggingcounter=templaggingcounter
                        if((laggingcounter>maxlaggingcounter/2) and (laggingrange>maxlaggingrange*2/3)):
                            resultdata_list.append([stockinfo, A_Bratio, stockrange, comrange, laggingrange, laggingcounter, maxlaggingrange, maxlaggingcounter, lagging30range, lagging30counter, lagging60range, lagging60counter, lagging100range, lagging100counter, lagging200range, lagging200counter, lagging500range, lagging500counter])
                    break
        write_csvfile(resultfile_path, title, resultdata_list)


def margin_Model_Select():
# 融资融券标的
    marginfile_path = os.path.join(margindata_path , end_time+".csv")

    def get_margindata():
        margin_url = "http://stock.jrj.com.cn/action/rzrq/getTransDetailByTime.jspa?vname=detailData&day=1&havingType=1,2&page=1&psize=10000&sort=buy_sell_balance"
        marginData_title = ["股票名称", "融资买入比", "融资净买入比", "融券卖出比", "融券净卖出比"]
        marginData_list = []
        response = get_jsvar(margin_url, 'detailData')
        if(response!=None):
            for marginitem in response['data']:
                stockcode = marginitem[0]
                if(stockcode[:3]=='300'):
                    continue
                stock_name = marginitem[1]
                stockinfo = stock_name+'_'+stockcode
                rzye = float(marginitem[2])
                zltszb = float(marginitem[3])
                rzmre = float(marginitem[4])
                zcjeb = float(marginitem[5])
                rzche = float(marginitem[6])
                rqyl = float(marginitem[7])
                rqmcl = float(marginitem[8])
                rqchl = float(marginitem[9])
                rzrqye = float(marginitem[10])
                rzrqce = float(marginitem[11])
                rqylltb = float(marginitem[13])
                if(rzye==0):
                    rzmrb = 0
                    rzjmrb = 0
                else:
                    rzmrb = rzmre/rzye
                    rzjmrb = (rzmre-rzche)/rzye
                if(rqyl==0):
                    rqmcb = 0
                    rqjmcb = 0
                else:
                    rqmcb = rqmcl/rqyl
                    rqjmcb = (rqmcl-rqchl)/rqyl
                marginData_list.append([stockinfo, rzmrb, rzjmrb, rqmcb, rqjmcb])
            margin_title = ["日期", "股票代码", "融资余额", "融券余额", "融资买入额", "融券余量", "融资偿还额", "融券偿还量", "融券卖出量", "融资融券余额"]
            for ii in reversed(range(len(marginData_list))):
                try:
                    time.sleep(1)
                    margin_df = tspro.margin_detail(ts_code=gen_tscode(marginData_list[ii][0][-6:]), start_date=start_time, end_date=end_time)
                    margin_df = margin_df[["trade_date", "ts_code", "rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye"]]
                    margin_list = margin_df.values.tolist()
                    for jj in reversed(range(len(margin_list))):
                        if(np.isnan(margin_list[jj][2:]).any()):
                            margin_list.pop(jj)
                        else:
                            margin_list[jj][0] = margin_list[jj][0][0:4]+'-'+margin_list[jj][0][4:6]+'-'+margin_list[jj][0][6:8]
                    write_csvfile(os.path.join(margindata_path, marginData_list[ii][0]+'.csv'), margin_title, margin_list)
                except Exception as e:
                    print(e)
                    marginData_list.pop(ii)
                    time.sleep(600)
            write_csvfile(marginfile_path, marginData_title, marginData_list)
            return True
        else:
            return False

    resultfile_path = os.path.join(resultdata_path, "margin_Model_Select_Result.csv")
    title = ["股票名称", "1日净余额变化", "当前融资净余额", "融资净余额最近回升幅度", "回升股价变化", "最近回升天数", "融资净余额最近下降幅度", "下降股价变化", "最近下降天数", "融资净余额上一回升幅度", "回升股价变化", "上一回升天数", "融资净余额上一下降幅度", "下降股价变化", "上一下降天数"]
    resultdata_list = []
    if(get_margindata()):
        _, marginData_list = read_csvfile(marginfile_path)
        rounddaynum = 10
        for marginData in marginData_list:
            for filename in os.listdir(stockdata_path):
                if(marginData[0][-6:]==filename.split(".")[0][-6:]):
                    _, margin_list = read_csvfile(os.path.join(margindata_path, marginData[0]+'.csv'))
                    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    stockinfo = filename.split(".")[0]
                    closingprice = float(stockdata_list[0][3])
                    perioddaynum = min(400, len(margin_list))
                    rounddaynum = 10
                    if(perioddaynum<50):
                        break
                    rzjye_list = [(float(margin_list[ii][2])-float(margin_list[ii][3])) for ii in range(perioddaynum)]
                    rzjyerange = ((rzjye_list[0]/rzjye_list[1])-1)*100
                    minoffset = perioddaynum-1
                    maxoffset = perioddaynum-1
                    minrzjye_list = []
                    minprice_list = []
                    minrzjyeoffset_list = []
                    minpriceoffset_list = []
                    maxrzjye_list = []
                    maxprice_list = []
                    maxrzjyeoffset_list = []
                    maxpriceoffset_list = []
                    startoffset = perioddaynum-1
                    for ii in range(perioddaynum):
                        if(rzjye_list[ii]==min(rzjye_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])):
                            minrzjye_list.append(rzjye_list[ii])
                            minrzjyeoffset_list.append(ii)
                            startoffset = ii
                            isDrop = True
                            break
                    for ii in range(startoffset+1, perioddaynum):
                        tempmaxrzjye = max(rzjye_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])
                        tempminrzjye = min(rzjye_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])
                        if(isDrop):
                            if(rzjye_list[ii]==tempmaxrzjye):
                                maxrzjye_list.append(rzjye_list[ii])
                                maxrzjyeoffset_list.append(ii)
                                isDrop = False
                            elif((rzjye_list[ii]==tempminrzjye) and (rzjye_list[ii]<minrzjye_list[-1])):
                                minrzjye_list[-1]=rzjye_list[ii]
                                minrzjyeoffset_list[-1]=ii
                        else:
                            if(rzjye_list[ii]==tempminrzjye):
                                minrzjye_list.append(rzjye_list[ii])
                                minrzjyeoffset_list.append(ii)
                                isDrop = True
                            elif((rzjye_list[ii]==tempmaxrzjye) and (rzjye_list[ii]>maxrzjye_list[-1])):
                                maxrzjye_list[-1]=rzjye_list[ii]
                                maxrzjyeoffset_list[-1]=ii
                    for ii in range(len(minrzjyeoffset_list)):
                        for jj in range(len(stockdata_list)):
                            if(stockdata_list[jj][0]<=margin_list[minrzjyeoffset_list[ii]][0]):
                                minprice_list.append(float(stockdata_list[jj][3]))
                                minpriceoffset_list.append(jj)
                                break
                    for ii in range(len(maxrzjyeoffset_list)):
                        for jj in range(len(stockdata_list)):
                            if(stockdata_list[jj][0]<=margin_list[maxrzjyeoffset_list[ii]][0]):
                                maxprice_list.append(float(stockdata_list[jj][3]))
                                maxpriceoffset_list.append(jj)
                                break
                    if((len(minrzjye_list)>=2) and (len(maxrzjye_list)>=2)):
                        rzjyefailrange = (minrzjye_list[0]/maxrzjye_list[0]-1)*100
                        pricefailrange = (minprice_list[0]/maxprice_list[0]-1)*100
                        rzjyefailcounter = maxrzjyeoffset_list[0]-minrzjyeoffset_list[0]
                        rzjyereboundrange = (rzjye_list[0]/minrzjye_list[0]-1)*100
                        pricereboundrange = (closingprice/minprice_list[0]-1)*100
                        rzjyereboundcounter = minrzjyeoffset_list[0]
                        lastrzjyefailrange = (minrzjye_list[1]/maxrzjye_list[1]-1)*100
                        lastpricefailrange = (minprice_list[1]/maxprice_list[1]-1)*100
                        lastrzjyefailcounter = maxrzjyeoffset_list[1]-minrzjyeoffset_list[1]
                        lastrzjyereboundrange = (maxrzjye_list[0]/minrzjye_list[1]-1)*100
                        lastpricereboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
                        lastrzjyereboundcounter = minrzjyeoffset_list[1]-maxrzjyeoffset_list[0]
                        if((rzjyefailrange<lastrzjyefailrange) and (rzjyefailcounter>lastrzjyefailcounter) and (3<rzjyereboundcounter) and (pricefailrange<-10)  and (pricereboundrange<abs(pricefailrange)/3)):
                            resultdata_list.append([stockinfo, rzjyerange, rzjye_list[0], rzjyereboundrange, pricereboundrange, rzjyereboundcounter, rzjyefailrange, pricefailrange, rzjyefailcounter,
                                                    lastrzjyereboundrange, lastpricereboundrange, lastrzjyereboundcounter, lastrzjyefailrange, lastpricefailrange, lastrzjyefailcounter])
                    break
        write_csvfile(resultfile_path, title, resultdata_list)


def block_Model_Select():
# 大宗交易数据
    resultfile_path = os.path.join(resultdata_path, "block_Model_Select_Result.csv")
    title = ["股票名称", "交易日期", "交易溢价率(%)", "交易后最大涨幅(%)", "交易后最大跌幅(%)", "交易换手率(%)", "交易/当日量比", "交易/今日量比", "成交金额(万元)", "买方营业部", "卖方营业部"]
    resultdata_list = []
    block_list = []
    for ii in range(3):
        try:
            time.sleep(1)
            block_df = tspro.block_trade(start_date=start_time, end_date=end_time)
            block_df.dropna(axis=0, how='any', thresh=None, subset=None, inplace=True)
            block_list = block_df.values.tolist()
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    for ii in range(len(block_list)):
        if((block_list[ii][0][:3]!="300") and (block_list[ii][-2][:4]!=block_list[ii][-1][:4])):
            for filename in os.listdir(stockdata_path):
                stockinfo = filename.split(".")[0]
                if(block_list[ii][0][:6]==stockinfo[-6:]):
                    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    block_list[ii][1] = block_list[ii][1][0:4] + '-' + block_list[ii][1][4:6] + '-' + block_list[ii][1][6:8]
                    blockoffset = 0
                    for jj in range(len(stockdata_list)):
                        if(stockdata_list[jj][0]==block_list[ii][1]):
                            blockoffset = jj
                            break
                    closingprice_list = [float(item[3]) for item in stockdata_list[:(blockoffset+1)]]
                    convpre = (float(block_list[ii][2])/closingprice_list[blockoffset]-1)*100
                    volumnratio1 = (float(block_list[ii][4])*10000/float(stockdata_list[blockoffset][11]))
                    tradevolumn = volumnratio1*float(stockdata_list[blockoffset][10])
                    volumnratio2 = tradevolumn/float(stockdata_list[0][10])
                    riserange = (max(closingprice_list)/closingprice_list[blockoffset]-1)*100
                    failrange = (min(closingprice_list)/closingprice_list[blockoffset]-1)*100
                    resultdata_list.append([stockinfo, stockdata_list[blockoffset][0], convpre, riserange, failrange, tradevolumn, volumnratio1, volumnratio2, block_list[ii][4], block_list[ii][5], block_list[ii][6]])
                    break
    write_csvfile(resultfile_path, title, resultdata_list)


def get_MonthData(stockdata_list):
    monthstr = ""
    monthoffset_list = []
    for ii in range(len(stockdata_list)):
        if(stockdata_list[ii][0].split("-")[1]!=monthstr):
            monthstr = stockdata_list[ii][0].split("-")[1]
            monthoffset_list.append(ii)
    monthclosingprice_list = [float(stockdata_list[offset][3]) for offset in monthoffset_list]
    monthoffset_list.append(len(stockdata_list))
    monthupperprice_list = [max([float(stockdata_list[jj][4]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    monthlowerprice_list = [min([float(stockdata_list[jj][5]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    monthvolumn_list = [sum([float(stockdata_list[jj][10]) for jj in range(monthoffset_list[ii], monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    return monthclosingprice_list, monthupperprice_list, monthlowerprice_list, monthvolumn_list


def volumnMonth_Model_Select():
# 放量模型
    resultfile_path = os.path.join(resultdata_path, "volumnMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "前前月涨跌幅", "放量倍数", "历史位置", "历史最大放量倍数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(volumnMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def volumnMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "volumnMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "前前月涨跌幅", "放量倍数", "历史位置", "历史最大放量倍数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(volumnMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def volumnMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, _, _, monthvolumn_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthvolumn = monthvolumn_list[0]
    monthvolumn_list = monthvolumn_list[1:]
    periodmonthnum = min(36, len(monthclosingprice_list)-2)
    if(periodmonthnum<5):
        return []
    volumnratio1 = monthvolumn_list[0]/monthvolumn_list[1]
    if(volumnratio1>2):
        reboundrange = (monthclosingprice_list[0]-min(monthclosingprice_list))/(max(monthclosingprice_list)-min(monthclosingprice_list))*100
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        monthrange2 = (monthclosingprice_list[1]/monthclosingprice_list[2]-1)*100
        maxvolumnratio1 = 0
        for ii in range(2, periodmonthnum):
            tempvolumnratio1 = monthvolumn_list[ii]/monthvolumn_list[ii+1]
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
        if(reboundrange<30):
            return [stockinfo, monthrange0, monthrange1, monthrange2, volumnratio1, reboundrange, maxvolumnratio1]
    return []


def vshapeMonth_Model_Select():
# 放量上涨模型
    resultfile_path = os.path.join(resultdata_path, "vshapeMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨幅", "前前月跌幅", "放量倍数", "相对放量倍数", "历史位置", "历史最大放量倍数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(vshapeMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def vshapeMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "vshapeMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨幅", "前前月跌幅", "放量倍数", "相对放量倍数", "历史位置", "历史最大放量倍数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(vshapeMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def vshapeMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, _, _, monthvolumn_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthvolumn = monthvolumn_list[0]
    monthvolumn_list = monthvolumn_list[1:]
    periodmonthnum = min(36, len(monthclosingprice_list)-2)
    if(periodmonthnum<5):
        return []
    monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
    monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
    monthrange2 = (monthclosingprice_list[1]/monthclosingprice_list[2]-1)*100
    if((monthrange1>0) and (monthrange2<0) and (abs(monthrange1)/abs(monthrange2)>1/4)):
        volumnratio1 = monthvolumn_list[0]/monthvolumn_list[1]
        volumnratio2 = abs((monthvolumn_list[0]*monthrange2)/(monthrange1*monthvolumn_list[1]))
        reboundrange = (monthclosingprice_list[0]-min(monthclosingprice_list))/(max(monthclosingprice_list)-min(monthclosingprice_list))*100
        maxvolumnratio1 = 0
        for ii in range(2, periodmonthnum):
            tempvolumnratio1 = monthvolumn_list[ii]/monthvolumn_list[ii+1]
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
        if((volumnratio1>1) and (volumnratio2>1.5) and (reboundrange<30)):
            return [stockinfo, monthrange0, monthrange1, monthrange2, volumnratio1, volumnratio2, reboundrange, maxvolumnratio1]
    return []


def shadowMonth_Model_Select():
# 收下影线金针探底模型
    resultfile_path = os.path.join(resultdata_path, "shadowMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "前月下影线幅度", "放量倍数", "历史位置", "历史最大放量倍数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(shadowMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def shadowMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "shadowMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "前月下影线幅度", "放量倍数", "历史位置", "历史最大放量倍数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(shadowMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def shadowMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthupperprice_list, monthlowerprice_list, monthvolumn_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthupperprice = monthupperprice_list[0]
    monthupperprice_list = monthupperprice_list[1:]
    monthlowerprice = monthlowerprice_list[0]
    monthlowerprice_list = monthlowerprice_list[1:]
    monthvolumn = monthvolumn_list[0]
    monthvolumn_list = monthvolumn_list[1:]
    periodmonthnum = min(36, len(monthclosingprice_list)-2)
    if(periodmonthnum<5):
        return []
    shadowratio = (min(monthclosingprice_list[0], monthclosingprice_list[1])-monthlowerprice_list[0])/(monthupperprice_list[0]-monthlowerprice_list[0])
    shadowrange = (min(monthclosingprice_list[0], monthclosingprice_list[1])-monthlowerprice_list[0])/monthclosingprice_list[1]*100
    if(shadowratio>0.8):
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        volumnratio1 = monthvolumn_list[0]/monthvolumn_list[1]
        reboundrange = (monthclosingprice_list[0]-min(monthclosingprice_list))/(max(monthclosingprice_list)-min(monthclosingprice_list))*100
        maxvolumnratio1 = 0
        for ii in range(2, periodmonthnum):
            tempvolumnratio1 = monthvolumn_list[ii]/monthvolumn_list[ii+1]
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
        if(reboundrange<30):
            return [stockinfo, monthrange0, monthrange1, shadowrange, volumnratio1, reboundrange, maxvolumnratio1]
    return []


def dropMonth_Model_Select():
# 月连续跌幅
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "连续跌幅月数", "月累计总跌幅", "放量倍数", "收盘价连续最低月数", "最低价连续最低月数", "最多连续跌幅月数", "最大月连续跌幅", "历史最大放量倍数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(dropMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "连续跌幅月数", "月累计总跌幅", "放量倍数", "收盘价连续最低月数", "最低价连续最低月数", "最多连续跌幅月数", "最大月连续跌幅", "历史最大放量倍数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(dropMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, _, monthlowerprice_list, monthvolumn_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthlowerprice = monthlowerprice_list[0]
    monthlowerprice_list = monthlowerprice_list[1:]
    monthvolumn = monthvolumn_list[0]
    monthvolumn_list = monthvolumn_list[1:]
    periodmonthnum = min(36, len(monthclosingprice_list)-2)
    if(periodmonthnum<5):
        return []
    modelcounter = 0
    for ii in range(periodmonthnum):
        if(monthclosingprice_list[ii]<=monthclosingprice_list[ii+1]):
            modelcounter += 1
        else:
            break
    if(modelcounter>3):
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        monthvolumnratio1 = monthvolumn_list[0]/monthvolumn_list[1]
        monthclosingcounter = 0
        monthlowercounter = 0
        for ii in range(1, periodmonthnum):
            if(monthlowerprice_list[0]<=monthclosingprice_list[ii]):
                monthlowercounter += 1
            else:
                break
        for ii in range(1, periodmonthnum):
            if(monthclosingprice_list[0]<=monthclosingprice_list[ii]):
                monthclosingcounter += 1
            else:
                break
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum):
                if(monthclosingprice_list[jj]<=monthclosingprice_list[jj+1]):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxvolumnratio1 = 0
        for ii in range(2, periodmonthnum):
            tempvolumnratio1 = monthvolumn_list[ii]/monthvolumn_list[ii+1]
            if(maxvolumnratio1<tempvolumnratio1):
                maxvolumnratio1 = tempvolumnratio1
        if((modelrange<maxmodelrange*2/3) and (monthvolumnratio1>1)):
            return [stockinfo, monthrange0, monthrange1, modelcounter, modelrange, monthvolumnratio1, monthclosingcounter, monthlowercounter, maxmodelcounter, maxmodelrange, maxvolumnratio1]
    return []


def KDJMonth_Model_Select():
# 月 KDJ 模型 n=9
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "历史最大下方月数", "历史最大上穿前跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "历史最大下方月数", "历史最大上穿前跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_pipeline(filename):
    N = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthupperprice_list, monthlowerprice_list, _ = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthupperprice = monthupperprice_list[0]
    monthupperprice_list = monthupperprice_list[1:]
    monthlowerprice = monthlowerprice_list[0]
    monthlowerprice_list = monthlowerprice_list[1:]
    periodmonthnum = min(100, len(monthclosingprice_list)-N)
    if(periodmonthnum<10):
        return []
    K_list = [50]*(periodmonthnum+1)
    D_list = [50]*(periodmonthnum+1)
    J_list = [50]*periodmonthnum
    DIFF_list = [0]*periodmonthnum
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(periodmonthnum)):
        C9 = monthclosingprice_list[ii]
        H9 = max(monthupperprice_list[ii:ii+9])
        L9 = min(monthlowerprice_list[ii:ii+9])
        RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[ii+1]+1/3*RSV
        D = 2/3*D_list[ii+1]+1/3*K
        J = 3*K-2*D
        K_list[ii] = K
        D_list[ii] = D
        J_list[ii] = J
        DIFF_list[ii] = K-D
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        modelpredict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        modelslope = (DIFF_list[0]-DIFF_list[1])/monthclosingprice_list[0]
        Kprice = (H9-L9)*K_list[0]/100+L9
        Krange = (Kprice/monthclosingprice_list[0]-1)*100
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, monthrange0, monthrange1, round(modelpredict,2), modelcounter, modelrange, modelslope, Krange, K_list[0], D_list[0], J_list[0], RSV,maxmodelcounter, maxmodelrange]
    return []


def CCIMonth_Model_Select():
# 月 CCI 模型 n=14
    resultfile_path = os.path.join(resultdata_path, "CCIMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "CCI上涨月数", "CCI上涨幅度", "CCI下跌月数", "CCI下跌幅度", "当月CCI", "历史最大下跌月数", "历史最大下跌幅度"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(CCIMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def CCIMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "CCIMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "CCI上涨月数", "CCI上涨幅度", "CCI下跌月数", "CCI下跌幅度", "当月CCI", "历史最大下跌月数", "历史最大下跌幅度"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(CCIMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def CCIMonth_Model_Select_pipeline(filename):
    N = 14
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthupperprice_list, monthlowerprice_list, _ = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    monthupperprice = monthupperprice_list[0]
    monthupperprice_list = monthupperprice_list[1:]
    monthlowerprice = monthlowerprice_list[0]
    monthlowerprice_list = monthlowerprice_list[1:]
    periodmonthnum = min(100, len(monthclosingprice_list)-N)
    if(periodmonthnum<10):
        return []
    TP_list = [0]*(periodmonthnum+N)
    MA_list = [0]*periodmonthnum
    MD_list = [0]*periodmonthnum
    CCI_list = [0]*periodmonthnum
    maxprice_list = []
    minprice_list = []
    maxoffset_list = []
    minoffset_list = []
    for ii in range(periodmonthnum+N):
        TP_list[ii] = (monthclosingprice_list[ii]+monthupperprice_list[ii]+monthlowerprice_list[ii])/3
    for ii in range(periodmonthnum):
        MA_list[ii] = np.mean(TP_list[ii:ii+N])
        MD_list[ii] = np.mean(np.abs([TP_list[jj]-MA_list[ii] for jj in range(ii,ii+N)]))
        CCI_list[ii] = (TP_list[ii]-MA_list[ii])/MD_list[ii]/0.015
    for ii in range(1, periodmonthnum-1):
        if((CCI_list[ii]>CCI_list[ii-1]) and (CCI_list[ii]>CCI_list[ii+1])):
            maxprice_list.append(monthclosingprice_list[ii])
            maxoffset_list.append(ii)
        if((CCI_list[ii]<CCI_list[ii-1]) and (CCI_list[ii]<CCI_list[ii+1])):
            minprice_list.append(monthclosingprice_list[ii])
            minoffset_list.append(ii)
    if((len(minoffset_list)>3) and (len(maxoffset_list)>3) and (minoffset_list[0]<maxoffset_list[0])):
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        reboundrange = (monthclosingprice_list[0]/minprice_list[0]-1)*100
        reboundcounter = minoffset_list[0]
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(failcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum-1):
                if(CCI_list[jj]<CCI_list[jj+1]):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(failrange<maxmodelrange*2/3):
            return [stockinfo, monthrange0, monthrange1, reboundcounter, reboundrange, failcounter, failrange, CCI_list[0], maxmodelcounter, maxmodelrange]
    return []


def BOLLMonth_Model_Select():
# BOLL 模型 N1=20 N2=2
    resultfile_path = os.path.join(resultdata_path, "BOLLMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "BOLL极限宽", "BOLL下方月数", "BOLL下方涨跌幅", "上一BOLL下穿上轨月数", "下穿涨跌幅", "上一BOLL上穿下轨月数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(BOLLMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLLMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "BOLLMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "BOLL极限宽", "BOLL下方月数", "BOLL下方涨跌幅", "上一BOLL下穿上轨月数", "下穿涨跌幅", "上一BOLL上穿下轨月数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(BOLLMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLLMonth_Model_Select_pipeline(filename):
    N1 = 20
    N2 = 2
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthupperprice_list, monthlowerprice_list, _ = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = min(100, len(monthclosingprice_list)-N1)
    if(periodmonthnum<20):
        return []
    MA_list = [0]*periodmonthnum
    STD_list = [0]*periodmonthnum
    WIDTH_list = [0]*periodmonthnum
    UP_list = [0]*periodmonthnum
    DN_list = [0]*periodmonthnum
    for ii in range(periodmonthnum):
        MA_list[ii] = np.mean(monthclosingprice_list[ii:ii+N1])
        STD_list[ii] = np.std(monthclosingprice_list[ii:ii+N1])
        UP_list[ii] = MA_list[ii]+STD_list[ii]*N2
        DN_list[ii] = MA_list[ii]-STD_list[ii]*N2
        WIDTH_list[ii] = (UP_list[ii]-DN_list[ii])/MA_list[ii]
    if((monthclosingprice_list[1]<DN_list[1]) or (monthclosingprice_list[0]<DN_list[0]) or (monthclosingprice<DN_list[0])):
        modelcounter = 1
        for ii in range(1, periodmonthnum):
            if(monthclosingprice_list[ii]<DN_list[ii]):
                modelcounter += 1
            else:
                break
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        upoffset = 0
        for ii in range(modelcounter, periodmonthnum):
            if((monthclosingprice_list[ii]>UP_list[ii]) and (monthclosingprice_list[ii-1]<UP_list[ii])):
                upoffset = ii
                break
        uprange = (monthclosingprice_list[0]/monthclosingprice_list[upoffset]-1)*100
        dnoffset = 0
        for ii in range(modelcounter, periodmonthnum):
            if((monthclosingprice_list[ii]<DN_list[ii]) and (monthclosingprice_list[ii-1]>DN_list[ii-1])):
                dnoffset = ii
                break
        dnrange = (monthclosingprice_list[0]/monthclosingprice_list[dnoffset]-1)*100
        widthrange = (WIDTH_list[0]/WIDTH_list[10]-1)*100
        marange = (MA_list[0]/MA_list[10]-1)*100
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        return [stockinfo, monthrange0, monthrange1, WIDTH_list[0], modelcounter, modelrange, upoffset, uprange, dnoffset, dnrange, widthrange, marange]
    return []


def MACDDIFFMonth_Model_Select():
# MACD 模型 (12,26,9)
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "前月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "上穿前总跌幅", "MACD斜率", "DEA比例", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最低DEA比例", "历史最低相对DEA比例"]
    title2 = ["股票名称", "当月涨跌幅", "前月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "上穿前总跌幅", "DIFF斜率", "DEA比例", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最低DEA比例", "历史最低相对DEA比例"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFFMonth_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFFMonth_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "前月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "上穿前总跌幅", "MACD斜率", "DEA比例", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最低DEA比例", "历史最低相对DEA比例"]
    title2 = ["股票名称", "当月涨跌幅", "前月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "上穿前总跌幅", "DIFF斜率", "DEA比例", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最低DEA比例", "历史最低相对DEA比例"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFFMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFFMonth_Model_Select_pipeline(filename):
    N1 = 12
    N2 = 26
    N3 = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, _, _, _ = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = len(monthclosingprice_list)-1
    if(periodmonthnum<20):
        return [], []
    MACD_result = []
    DIFF_result = []
    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para(monthclosingprice_list, N1, N2, N3)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        modelcounter = 1
        for ii in range(1, periodmonthnum):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                modelcounter+=1
            else:
                break
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        modelpredict = MACD_list[0]/(MACD_list[1]-MACD_list[0])
        modelslope = (MACD_list[0]-MACD_list[1])/monthclosingprice_list[0]
# Solve Function (DIFF(new)-DEA(new))*2 = MACD (i.e. 0, MACD_list[0], 2*MACD_list[0]-MACD_list[1])
# DIFF(new)-((N3-1)/(N3+1)*DEA_list[0]+2/(N3+1)*DIFF(new)) = MACD/2
# (N3-1)/(N3+1)*(DIFF(new)*DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(EMA1(new)-EMA2(new)-DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0]) = MACD/2
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0] = MACD/2*(N3+1)/(N3-1)
# x =  (MACD/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossprice = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossrange = (crossprice/monthclosingprice_list[0]-1)*100
        trendprice = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trendrange = (trendprice/monthclosingprice_list[0]-1)*100
        parallelprice = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallelrange = (parallelprice/monthclosingprice_list[0]-1)*100
        DEA = min(DEA_list[:modelcounter])
        minDEA = min(DEA_list[:periodmonthnum])
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:periodmonthnum])
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum):
                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            MACD_result = [stockinfo, monthrange0, monthrange1, round(modelpredict,2), modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange,2, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAratio]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                modelcounter+=1
            else:
                break
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        modelpredict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        modelslope = (DIFF_list[0]-DIFF_list[1])/monthclosingprice_list[0]
# Solve Function DIFF(new) = DIFF (i.e. 0, DIFF_list[0], 2*DIFF_list[0]-DIFF_list[1])
# EMA1(new)-EMA2(new) = DIFF
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x) = DIFF
# x = (DIFF+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossprice = ((N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossrange = (crossprice/monthclosingprice_list[0]-1)*100
        trendprice = ((2*DIFF_list[0]-DIFF_list[1])+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trendrange = (trendprice/monthclosingprice_list[0]-1)*100
        parallelprice = (DIFF_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallelrange = (parallelprice/monthclosingprice_list[0]-1)*100
        DEA = min(DEA_list[:modelcounter])
        minDEA = min(DEA_list[:periodmonthnum])
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:periodmonthnum])
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            DIFF_result = [stockinfo, monthrange0, monthrange1, round(modelpredict,2), modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAratio]
    return MACD_result, DIFF_result


def trendMonth_Model_Select():
# K线图 1月线 贯穿 5月线  可拓展为 N1月线 贯穿 N2月线
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "1月线上穿预测月数", "5月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "1月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "5月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth_Model_Select_par():
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "1月线上穿预测月数", "5月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "1月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "前月涨跌幅", "5月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "DIFF", "DIFF比例", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅", "历史最大下方月数", "历史最大上穿前跌幅", "历史最大DIFF", "历史最大DIFF比例"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10Month_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5Month_Model_Select_pipeline(filename):
    return trendMonth_Model_Select_pipeline(filename, 1, 5)
def trend1T10Month_Model_Select_pipeline(filename):
    return trendMonth_Model_Select_pipeline(filename, 1, 10)
def trend5T10Month_Model_Select_pipeline(filename):
    return trendMonth_Model_Select_pipeline(filename, 5, 10)
def trendMonth_Model_Select_pipeline(filename, N1, N2):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, _, _, _ = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = len(monthclosingprice_list)-N2
    if(periodmonthnum<10):
        return []
    MA1_list = [0]*periodmonthnum
    MA2_list = [0]*periodmonthnum
    DIFF_list = [0]*periodmonthnum
    DIFFratio_list = [0]*periodmonthnum
    for ii in range(periodmonthnum):
        MA1 = np.mean(monthclosingprice_list[ii:ii+N1])
        MA2 = np.mean(monthclosingprice_list[ii:ii+N2])
        DIFF = MA1-MA2
        MA1_list[ii] = MA1
        MA2_list[ii] = MA2
        DIFF_list[ii] = DIFF
        DIFFratio_list[ii] = DIFF/monthclosingprice_list[ii]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        modelcounter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                modelcounter += 1
            else:
                break
        modelrange = (monthclosingprice_list[0]/monthclosingprice_list[modelcounter]-1)*100
        modelpredict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
# Solve Function MA1(new)-MA2(new)=DIFF  (i.e. 0, DIFF_list[0], 2DIFF_list[0]-DIFF_list[1])
# (x+sum(monthclosingprice_list[:N1-1]))/N1 - (x+sum(monthclosingprice_list[:N2-1]))/N2 = DIFF 
# x = (DIFF+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        crossprice = (sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        crossrange = (crossprice/monthclosingprice_list[0]-1)*100
        trendprice = ((2*DIFF_list[0]-DIFF_list[1])+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trendrange = (trendprice/monthclosingprice_list[0]-1)*100
        parallelprice = (DIFF_list[0]+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallelrange = (parallelprice/monthclosingprice_list[0]-1)*100
        minDIFF = min(DIFF_list[:periodmonthnum])
        minDIFFratio = min(DIFFratio_list[:periodmonthnum])
        monthrange0 = (monthclosingprice/monthclosingprice_list[0]-1)*100
        monthrange1 = (monthclosingprice_list[0]/monthclosingprice_list[1]-1)*100
        maxmodelcounter = 0
        maxmodelrange = 0
        for ii in range(modelcounter, periodmonthnum):
            tempmodelcounter = 0
            tempmodelrange = 0
            for jj in range(ii, periodmonthnum):
                if(DIFF_list[jj]<0):
                    tempmodelcounter += 1
                else:
                    tempmodelrange = (monthclosingprice_list[ii]/monthclosingprice_list[ii+tempmodelcounter]-1)*100
                    if(maxmodelcounter<tempmodelcounter):
                        maxmodelcounter = tempmodelcounter
                    if(maxmodelrange>tempmodelrange):
                        maxmodelrange = tempmodelrange
                    break
        if(modelrange<maxmodelrange*2/3):
            return [stockinfo, monthrange0, monthrange1, round(modelpredict,2), modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDIFF, minDIFFratio]
    return []


def clear_data():
    if(not os.path.exists(stockdata_path)):
        os.mkdir(stockdata_path)
    for filename in os.listdir(stockdata_path):
        filepath = os.path.join(stockdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(resultdata_path)):
        os.mkdir(resultdata_path)
    for filename in os.listdir(resultdata_path):
        filepath = os.path.join(resultdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(HKdata_path)):
        os.mkdir(HKdata_path)
    for filename in os.listdir(HKdata_path):
        filepath = os.path.join(HKdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(Bdata_path)):
        os.mkdir(Bdata_path)
    for filename in os.listdir(Bdata_path):
        filepath = os.path.join(Bdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(margindata_path)):
        os.mkdir(margindata_path)
    for filename in os.listdir(margindata_path):
        filepath = os.path.join(margindata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(indexdata_path)):
        os.mkdir(indexdata_path)
    for filename in os.listdir(indexdata_path):
        filepath = os.path.join(indexdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    if(not os.path.exists(querydata_path)):
        os.mkdir(querydata_path)
    for filename in os.listdir(querydata_path):
        filepath = os.path.join(querydata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def generate_query():
    selectfile_list = os.listdir(resultdata_path)
    with open(stockinfo_file, 'r') as fp:
        for stockinfo in fp.readlines():
            stockinfo = stockinfo.strip()
            generate_query_pipeline(stockinfo)
def generate_query_par():
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    pool = multiprocessing.Pool(4)
    pool.map(generate_query_pipeline, stockinfo_list)
    pool.close()
    pool.join()
def generate_query_pipeline(stockinfo):
    selectfile_list = os.listdir(resultdata_path)
    query_list = []
    for resultfile in selectfile_list:
        resulttitle, resultdata_list = read_csvfile(os.path.join(resultdata_path, resultfile))
        for resultitem in resultdata_list:
            if(stockinfo==resultitem[0]):
                query_list.append([resultfile.split('_')[0]]+resulttitle)
                query_list.append([resultfile.split('_')[0]]+resultitem)
                query_list.append([','])
                break
    if(query_list!=[]):
        write_csvfile(os.path.join(querydata_path, stockinfo+'.csv'), [stockinfo], query_list)


def summary_result():
    selectfile_list = os.listdir(resultdata_path)
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    resultdata_list = []
    for stockinfo in stockinfo_list:
        resultdata_list.append(summary_result_pipeline(stockinfo))
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_par():
    selectfile_list = os.listdir(resultdata_path)
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(summary_result_pipeline, stockinfo_list)
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_pipeline(stockinfo):
    selectfile_list = os.listdir(resultdata_path)
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, selectfile_list[ii]))):
            selectfile_list.pop(ii)
    summary_list = []
    for ii in range(len(selectfile_list)):
        _, selectdata_list = read_csvfile(os.path.join(resultdata_path, selectfile_list[ii]))
        stockinfo_list = [item[0] for item in selectdata_list]
        if(stockinfo in stockinfo_list):
            summary_list.append(1)
        else:
            summary_list.append(0)
    if(sum(summary_list)>0):
        return [stockinfo, sum(summary_list)] + summary_list
    else:
        return []


def analyze_stockdata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Begin!")
#    EHBF_Analyze()
    EHBF_Analyze_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvalue_Model_Select Begin!")
    value_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvalue_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Begin!")
#    box_Model_Select()
    box_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Begin!")
#    wave_Model_Select()
    wave_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvolumn_Model_Select Begin!")
#    volumn_Model_Select()
    volumn_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvolumn_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Begin!")
#    shadow_Model_Select()
    shadow_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Begin!")    
#    vshape_Model_Select()
    vshape_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tparting_Model_Select Begin!")
#    parting_Model_Select()
    parting_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tparting_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Begin!")
#    drop_Model_Select()
    drop_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgap_Model_Select Begin!")
#    gap_Model_Select()
    gap_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgap_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trise_Model_Select Begin!")
#    rise_Model_Select()
    rise_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trise_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttangle_Model_Select Begin!")
#    tangle_Model_Select()
    tangle_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttangle_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Begin!")
#    trend_Model_Select()
    trend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
#    MACDDIFF_Model_Select()
    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Begin!")
#    KDJ_Model_Select()
    KDJ_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tCCI_Model_Select Begin!")
#    CCI_Model_Select()
    CCI_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tCCI_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLL_Model_Select Begin!")
#    BOLL_Model_Select()
    BOLL_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLL_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tPVI_Model_Select Begin!")
#    PVI_Model_Select()
    PVI_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tPVI_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEMV_Model_Select Begin!")
#    EMV_Model_Select()
    EMV_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEMV_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDMI_Model_Select Begin!")
#    DMI_Model_Select()
    DMI_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDMI_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tRSRS_Model_Select Begin!")
#    RSRS_Model_Select()
    RSRS_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tRSRS_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tOBV_Model_Select Begin!")
#    OBV_Model_Select()
    OBV_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tOBV_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvper_Model_Select Begin!")
#    obvper_Model_Select()
    obvper_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvper_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvtrend_Model_Select Begin!")
#    obvtrend_Model_Select()
    obvtrend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvtrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tstdper_Model_Select Begin!")
#    stdper_Model_Select()
    stdper_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tstdper_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tstdtrend_Model_Select Begin!")
#    stdtrend_Model_Select()
    stdtrend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tstdtrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tampper_Model_Select Begin!")
#    ampper_Model_Select()
    ampper_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tampper_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tamptrend_Model_Select Begin!")
#    amptrend_Model_Select()
    amptrend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tamptrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvMACD_Model_Select Begin!")
#    obvMACD_Model_Select()
    obvMACD_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobvMACD_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tlagging_Model_Select Begin!")
#    lagging_Model_Select()
    lagging_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tlagging_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvolumnMonth_Model_Select Begin!")
#    volumnMonth_Model_Select()
    volumnMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvolumnMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadowMonth_Model_Select Begin!")
#    shadowMonth_Model_Select()
    shadowMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadowMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshapeMonth_Model_Select Begin!")
#    vshapeMonth_Model_Select()
    vshapeMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshapeMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Begin!")
#    dropMonth_Model_Select()
    dropMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Begin!")
#    trendMonth_Model_Select()
    trendMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Begin!")
#    MACDDIFFMonth_Model_Select()
    MACDDIFFMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Begin!")
#    KDJMonth_Model_Select()
    KDJMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tCCIMonth_Model_Select Begin!")
#    CCIMonth_Model_Select()
    CCIMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tCCIMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLLMonth_Model_Select Begin!")
#    BOLLMonth_Model_Select()
    BOLLMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLLMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Begin!")
    AHCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Begin!")
    ABCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblock_Model_Select Begin!")
    block_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblock_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Begin!")
    margin_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Finished!")


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    if(isMarketOpen()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tIndex Data Download Begin!")
        get_163indexdata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tIndex Data Download Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Info Begin!")
        get_stockinfo()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Stock Info Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tStock Data Download Begin!")
        get_stockdata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tStock Data Download Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
        analyze_stockdata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Begin!")
#        summary_result()
        summary_result_par()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tQuery Generate Begin!")
#        generate_query()
        generate_query_par()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tQuery Generate Finished!")


if __name__=="__main__":
    main()