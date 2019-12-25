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
from scipy.stats import pearsonr


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
    title = ["日期", "收盘价", "最高价", "最低价", "开盘价", "成交量", "涨跌幅"]
    yahoo_url = "https://finance.yahoo.com/quote/{}.HK/history?period1={}&period2={}&interval=1d&filter=history&frequency=1d".format(stockHcode[-4:],int(time.mktime(time.strptime(start_time,"%Y%m%d"))),int(time.mktime(time.strptime(end_time,"%Y%m%d"))))
    response = get_htmltext(yahoo_url)
    if(response!=""):
        soup = BeautifulSoup(response, "lxml")
        script_json = json.loads(soup.find_all('script')[-3].text.split("\n")[5][16:-1])
        prices_json = script_json['context']['dispatcher']['stores']['HistoricalPriceStore']['prices']
        prices_df = pd.DataFrame(prices_json)
        if(len(prices_df)>0):
            prices_df.sort_values(['date', 'close'], ascending=[False,False],inplace = True)
            prices_df['date'] = prices_df['date'].apply(lambda x: dt.date.fromtimestamp(x).strftime('%Y-%m-%d'))
            prices_list = []
            if(prices_df.shape[1]>7):
                prices_df = prices_df[["date", "close", "high", "low", "open", "volume", "data", "type"]]
                prices_list = prices_df.values.tolist()
                prices_list[-1] = prices_list[-1][:6] + [0]
                for ii in reversed(range(len(prices_list)-1)):
                    if(prices_list[ii][-1]=="DIVIDEND"):
                        proportion = (prices_list[ii+1][1]-prices_list[ii][-2])/prices_list[ii+1][1]
                        prices_list.pop(ii)
                        for jj in range(ii, len(prices_list)):
                            prices_list[jj][1] = prices_list[jj][1]*proportion
                            prices_list[jj][2] = prices_list[jj][2]*proportion
                            prices_list[jj][3] = prices_list[jj][3]*proportion
                            prices_list[jj][4] = prices_list[jj][4]*proportion
                    elif(prices_list[ii][-1]=="SPLIT"):
                        prices_list.pop(ii)
                    elif(np.isnan(prices_list[ii][1:5]).all()):
                        prices_list.pop(ii)
#                    elif(not np.isnan(prices_list[ii][-1])):
#                        print("ERROR Except SPLIT&DIVIDEND")
#                        print(stockHcode)
                    else:
                        prices_list[ii] = prices_list[ii][:6] + [(prices_list[ii][1]/prices_list[ii+1][1]-1)*100]
            else:
                prices_df = prices_df[["date", "close", "high", "low", "open", "volume"]]
                prices_list = prices_df.values.tolist()
                prices_list[-1] = prices_list[-1][:6] + [0]
                for ii in reversed(range(len(prices_list)-1)):
                    if(np.isnan(prices_list[ii][1:5]).all()):
                        prices_list.pop(ii)
                    else:
                        prices_list[ii] = prices_list[ii][:6] + [(prices_list[ii][1]/prices_list[ii+1][1]-1)*100]                        
            write_csvfile(filename, title, prices_list)
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
            if("*ST" in CSIAll_list[ii]['stockname']):
                CSIAll_list[ii]['stockname'] = CSIAll_list[ii]['stockname'].replace("*ST", "")
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
# 横盘天数 & 振幅 & EMA & MAOBV & PE & PB
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "历史位置(%)", "总交易日", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "10日标准差", "20日标准差", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅", "平均20日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
    for jj in range(3):
        try:
            df_todays = tspro.daily_basic(trade_date=end_time, fields='ts_code,pe,pe_ttm,pb,ps,ps_ttm')
            for ii in range(len(resultdata_list)):
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
                resultdata_list[ii] = resultdata_list[ii] + [stock_pb, stock_pe, stock_pettm, stock_ps, stock_psttm]
            title = title + ["市净率(pb)", "市盈率(pe)", "pe(TTM)", "市销率(ps)", "ps(TTM)"]
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    for ii in range(len(resultdata_list)):
        time.sleep(random.choice([1.2,2]))
        stockcode = resultdata_list[ii][0][-6:]
        stock_pledge = np.nan
        try:
            df_pledge = tspro.pledge_stat(ts_code=gen_tscode(stockcode))
            if(not df_pledge.empty):
                stock_pledge = df_pledge["pledge_ratio"].values[0]
            break
        except Exception as e:
            time.sleep(600)
            print(e)
        resultdata_list[ii] = resultdata_list[ii] + [stock_pledge]
    title = title + ["股权质押比例"]
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "历史位置(%)", "总交易日", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "10日标准差", "20日标准差", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅", "平均20日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    for jj in range(3):
        try:
            df_todays = tspro.daily_basic(trade_date=end_time, fields='ts_code,pe,pe_ttm,pb,ps,ps_ttm')
            for ii in range(len(resultdata_list)):
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
                resultdata_list[ii] = resultdata_list[ii] + [stock_pb, stock_pe, stock_pettm, stock_ps, stock_psttm]
            title = title + ["市净率(pb)", "市盈率(pe)", "pe(TTM)", "市销率(ps)", "ps(TTM)"]
            break
        except Exception as e:
            print(e)
            time.sleep(600)
    for ii in range(len(resultdata_list)):
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
                time.sleep(600)
                print(e)
        resultdata_list[ii] = resultdata_list[ii] + [stock_pledge]
    title = title + ["股权质押比例"]
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    def EMA_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(100, len(stockdata_list))
        EMA6 = 0
        EMA12 = 0
        EMA24 = 0
        for ii in reversed(range(perioddaynum)):
            EMA6 = 2/7*float(stockdata_list[ii][3]) + 5/7*EMA6
            EMA12 = 2/13*float(stockdata_list[ii][3]) + 11/13*EMA12
            EMA24 = 2/25*float(stockdata_list[ii][3]) + 23/25*EMA24
        EMA6_range = (closingprice - EMA6) / EMA6 * 100
        EMA12_range = (closingprice - EMA12) / EMA12 * 100
        EMA24_range = (closingprice - EMA24) / EMA24 * 100
        return EMA6_range, EMA12_range, EMA24_range

    def earnratio_Analyze(stockdata_list):
        obv_dict = {}
        closingprice = float(stockdata_list[0][3])
        upperprice = max([float(item[4]) for item in stockdata_list])
        lowerprice = min([float(item[5]) for item in stockdata_list])
        for price in [item/100 for item in range(round(lowerprice*100), round((upperprice+0.01)*100))]:
            obv_dict[price] = 0
        for ii in range(len(stockdata_list)):
            maxprice = float(stockdata_list[ii][4])
            minprice = float(stockdata_list[ii][5])
            obv = float(stockdata_list[ii][10])
            aveobv = obv/((maxprice+0.01-minprice)*100)
            for price in [item/100 for item in range(round(minprice*100), round((maxprice+0.01)*100))]:
                obv_dict[price] += aveobv
        obv_sum = sum(obv_dict.values())
        supportobv = 0
        for price in [item/100 for item in range(round(max(closingprice*0.9,lowerprice)*100), round(closingprice*100))]:
            supportobv += obv_dict[price]
        supportratio = supportobv/obv_sum
        pressureobv = 0
        for price in [item/100 for item in range(round(closingprice*100), round(min(closingprice*1.1, upperprice)*100))]:
            pressureobv += obv_dict[price]
        pressureratio = pressureobv/obv_sum
        earnobv = 0
        for price in [item/100 for item in range(round(lowerprice*100), round(closingprice*100))]:
            earnobv += obv_dict[price]
        earnratio = earnobv/obv_sum
        return pressureratio, supportratio, earnratio
    
    def stable_Analyze(stockdata_list):
        closingprice_list = [float(item[3]) for item in stockdata_list]
        stable5counter = len(stockdata_list)
        stable10counter = len(stockdata_list)
        stable20counter = len(stockdata_list)
        for ii in range(1, len(stockdata_list)):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.05*maxprice):
                stable5counter = ii
                break
        for ii in range(stable5counter, len(stockdata_list)):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.1*maxprice):
                stable10counter = ii
                break
        for ii in range(stable10counter, len(stockdata_list)):
            minprice = min(closingprice_list[:ii+1])
            maxprice = max(closingprice_list[:ii+1])
            if((maxprice-minprice)>0.2*maxprice):
                stable20counter = ii
                break
        return stable5counter, stable10counter, stable20counter

    def std_Analyze(stockdata_list):
        std10 = np.std([float(item[3]) for item in stockdata_list[:min(10, len(stockdata_list))]])/np.mean([float(item[3]) for item in stockdata_list[:min(10, len(stockdata_list))]])
        std20 = np.std([float(item[3]) for item in stockdata_list[:min(20, len(stockdata_list))]])/np.mean([float(item[3]) for item in stockdata_list[:min(20, len(stockdata_list))]])
        return std10, std20

    def amplitude_Analyze(stockdata_list):
        amplitude10 = np.mean([((float(item[4])-float(item[5]))/float(item[7])*100) for item in stockdata_list[:10]])
        amplitude20 = np.mean([((float(item[4])-float(item[5]))/float(item[7])*100) for item in stockdata_list[:10]])
        return amplitude10, amplitude20

    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    closingprice_list = [float(item[3]) for item in stockdata_list]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
    stable5counter, stable10counter, stable20counter = stable_Analyze(stockdata_list)
    EMA6_range, EMA12_range, EMA24_range = EMA_Analyze(stockdata_list)
    std10, std20 = std_Analyze(stockdata_list)
    pressureratio, supportratio, earnratio = earnratio_Analyze(stockdata_list[:500])
    amplitude10, amplitude20 = amplitude_Analyze(stockdata_list)
    drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(30,len(stockdata_list)-1)][3]))/float(stockdata_list[min(30,len(stockdata_list)-1)][3])*100
    return [stockinfo, stockdata_list[0][9], reboundrange, len(stockdata_list), earnratio, pressureratio, supportratio, std10, std20, stable5counter, stable10counter, stable20counter, amplitude10, amplitude20, EMA6_range, EMA12_range, EMA24_range, drop30_range]


def drop_Model_Select():
# 连续多日跌幅模型
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "收盘价连续最低天数", "最低价连续最低天数", "百日位置(%)", "百日最多跌幅天数", "百日最大连续跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(drop_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "收盘价连续最低天数", "最低价连续最低天数", "百日位置(%)", "百日最多跌幅天数", "百日最大连续跌幅"]
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
    dropcounter = 0
    for ii in range(perioddaynum):
        if(float(stockdata_list[ii][9])<0):
            dropcounter += 1
        else:
            break
    if(dropcounter>0):
        droprange = (closingprice/closingprice_list[dropcounter]-1)*100
        lowerprice = float(stockdata_list[0][5])
        volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
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
        maxdropcounter = 0
        maxdroprange = 0
        for ii in range(dropcounter, min(100, perioddaynum)):
            tempdropcounter = 0
            for jj in range(ii, perioddaynum):
                if(float(stockdata_list[jj][9])<0):
                    tempdropcounter += 1
                else:
                    tempdroprange = (closingprice_list[ii]/closingprice_list[ii+tempdropcounter]-1)*100
                    if(tempdroprange<maxdroprange):
                        maxdroprange = tempdroprange
                    if(tempdropcounter>maxdropcounter):
                        maxdropcounter = tempdropcounter
                    break
        return [stockinfo, stockdata_list[0][9], dropcounter, droprange, volumnratio1, closingcounter, lowercounter, reboundrange, maxdropcounter, maxdroprange]
    else:
        return []


def rise_Model_Select():
# 连续多日上涨(&阳线)模型
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "收盘价连续最高天数", "最高价连续最高天数", "百日位置(%)", "百日最多涨幅天数", "百日最大连续涨幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(rise_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def rise_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "收盘价连续最高天数", "最高价连续最高天数", "百日位置(%)", "百日最多涨幅天数", "百日最大连续涨幅"]
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
    risecounter = 0
    for ii in range(perioddaynum):
#        if((float(stockdata_list[ii][9])>0) or (float(stockdata_list[ii][3])>float(stockdata_list[ii][6]))):
#        if(float(stockdata_list[ii][3])>float(stockdata_list[ii][6])):
        if(float(stockdata_list[ii][9])>0):
            risecounter += 1
        else:
            break
    if(risecounter>0):
        riserange = (closingprice/closingprice_list[risecounter]-1)*100
        upperprice = float(stockdata_list[0][4])
        maxprice = max(closingprice_list[:min(100, perioddaynum)])
        minprice = min(closingprice_list[:min(100, perioddaynum)])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
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
        maxrisecounter = 0
        maxriserange = 0
        for ii in range(risecounter, min(100, perioddaynum)):
            temprisecounter = 0
            for jj in range(ii, perioddaynum):
                if(float(stockdata_list[jj][9])>0):
                    temprisecounter += 1
                else:
                    tempriserange = (closingprice_list[ii]/closingprice_list[ii+temprisecounter]-1)*100
                    if(tempriserange>maxriserange):
                        maxriserange = tempriserange
                    if(temprisecounter>maxrisecounter):
                        maxrisecounter = temprisecounter
                    break
        return [stockinfo, stockdata_list[0][9], risecounter, riserange, volumnratio1, closingcounter, uppercounter, reboundrange, maxrisecounter, maxriserange]
    else:
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
        rebound_range = (closingprice-minprice)/(maxprice-minprice)*100
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
        return [stockinfo, rebound_range, volumnratio1, volumnratio2, stockdata_list[1][9], stockdata_list[0][9], maxvolumnratio1, maxvolumndate1, maxvolumnratio2, maxvolumndate2]
    else:
        return []


def shadow_Model_Select():
# 收下影线金针探底模型
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度", "百日位置(%)", "放量倍数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(shadow_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "上影线幅度", "百日位置(%)", "放量倍数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(shadow_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    maxprice = max([float(item[3]) for item in stockdata_list[:100]])
    minprice = min([float(item[3]) for item in stockdata_list[:100]])
    closingprice = float(stockdata_list[0][3])
    rebound_range = (closingprice-minprice)/(maxprice-minprice)*100
    open_range = (float(stockdata_list[0][6])-float(stockdata_list[0][7]))/float(stockdata_list[0][7])*100
    upper_range = (float(stockdata_list[0][4])-max(float(stockdata_list[0][3]), float(stockdata_list[0][6])))/float(stockdata_list[0][7])*100
    shadow_range = (min(float(stockdata_list[0][3]), float(stockdata_list[0][6]))-float(stockdata_list[0][5]))/float(stockdata_list[0][7])*100
    cylinder_range = (float(stockdata_list[0][3]) - float(stockdata_list[0][6]))/float(stockdata_list[0][7])*100
    volumnratio1 = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if((float(stockdata_list[0][9])<3) and (shadow_range>3) and (float(stockdata_list[0][5])<min([float(item[3]) for item in stockdata_list[:30]]))):
        return [stockinfo, stockdata_list[0][9], round(open_range,2), round(cylinder_range,2), round(shadow_range,2), round(rebound_range,2), round(upper_range,2), volumnratio1]
    else:
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
        max_offset = closingprice_list.index(maxprice)
        minprice = min(closingprice_list)
        min_offset = closingprice_list.index(minprice)
        if((min_offset>2) and (min_offset<max_offset) and (minprice<paratuple[1]*maxprice)):
            fail_range = (minprice-maxprice)/maxprice*100
            rebound_range = (closingprice-minprice)/maxprice*100
            rebound_ratio = -(rebound_range/fail_range)
            amountratio = sum([float(item[10]) for item in stockdata_list[:min_offset]])/sum([float(item[10]) for item in stockdata_list[min_offset:max_offset]])
            return [stockinfo, stockdata_list[0][9], fail_range, rebound_range, rebound_ratio, (max_offset-min_offset), min_offset, amountratio]
        else:
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
    perioddaynum = min(500, len(stockdata_list))
    if(perioddaynum<200):
        return [], []
    rounddaynum = 10
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
        return [stockinfo, stockdata_list[0][9], downwavecounter, upwavecounter, reboundrange, reboundcounter, failrange, failcounter, amountratio, wavevallratio, wavepeakratio,
                lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, lastamountratio, lastwavevallratio, lastwavepeakratio,
                sumreboundrange, sumreboundcounter, sumfailrange, sumfailcounter, sumamountratio, maxreboundrange, maxreboundcounter, maxfailrange, maxfailcounter]
    else:
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
        drop5_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        return [stockinfo, stockdata_list[0][9], volumnratio1, reboundrange, drop5_range, drop10_range, drop30_range, maxvolumnratio1, maxvolumndate1]
    else:
        return []


def trend_Model_Select():
# K线图 N1日线 贯穿 N2日线
    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend10T30_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend_Model_Select_par():
    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["股票名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "股票上穿前总跌幅", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅"]
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
    MA1_list = []
    MA2_list = []
    DIFF_list = []
    for ii in range(perioddaynum):
        MA1_list.append(np.mean([closingprice_list[ii:ii+N1]]))
        MA2_list.append(np.mean([closingprice_list[ii:ii+N2]]))
        DIFF_list.append(MA1_list[ii] - MA2_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (closingprice/closingprice_list[model_counter]-1)*100
        model_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
# Solve Function MA1(new)-MA2(new)=DIFF  (i.e. 0, DIFF_list[0], 2DIFF_list[0]-DIFF_list[1])
# (x+sum(closingprice_list[:N1-1]))/N1 - (x+sum(closingprice_list[:N2-1]))/N2 = DIFF 
# x = (DIFF+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        cross_price = (sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        cross_range = (cross_price/closingprice-1)*100
        trend_price = ((2*DIFF_list[0]-DIFF_list[1])+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trend_range = (trend_price/closingprice-1)*100
        parallel_price = (DIFF_list[0]+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallel_range = (parallel_price/closingprice-1)*100
        maxmodel_counter = 0
        maxmodel_range = 0
        for ii in range(model_counter, min(100, perioddaynum)):
            tempmodel_counter = 0
            tempmodel_range = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodel_counter += 1
                else:
                    tempmodel_range = (float(stockdata_list[ii][3])/float(stockdata_list[ii+tempmodel_counter][3])-1)*100
                    if(maxmodel_counter<tempmodel_counter):
                        maxmodel_counter = tempmodel_counter
                    if(maxmodel_range>tempmodel_range):
                        maxmodel_range = tempmodel_range
                    break
        return [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, round(cross_range,2), round(trend_range, 2), round(parallel_range,2), maxmodel_counter, maxmodel_range]
    else:
        return []


def KDJ_Model_Select():
# KDJ 模型 n=9
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "预测交叉涨跌幅", "KDJ斜率", "K值", "D值", "J值", "RSV", "百日最低J值", "日期", "百日最高J值", "日期"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJ_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "预测交叉涨跌幅", "KDJ斜率", "K值", "D值", "J值", "RSV", "百日最低J值", "日期", "百日最高J值", "日期"]
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
    K_list = [50]
    D_list = [50]
    J_list = [50]
    DIFF_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(perioddaynum)):
        C9 = float(stockdata_list[ii][3])
        H9 = max(upperprice_list[ii:ii+N])
        L9 = min(lowerprice_list[ii:ii+N])
        if(H9==L9):
            RSV = 50
        else:
            RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[0]+1/3*RSV
        D = 2/3*D_list[0]+1/3*K
        J = 3*K-2*D
        K_list.insert(0, K)
        D_list.insert(0, D)
        J_list.insert(0, J)
        DIFF_list.insert(0, K-D)
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (closingprice/closingprice_list[model_counter]-1)*100
        model_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        K_price = (H9-L9)*K_list[0]/100+L9
        K_range = (K_price/closingprice-1)*100
        model_slope = (DIFF_list[0]-DIFF_list[1])/((K_list[0]+D_list[0])/2)
        maxJ = max(J_list[:min(100, perioddaynum)])
        maxJdate = stockdata_list[J_list.index(maxJ)][0]
        minJ = min(J_list[:min(100, perioddaynum)])
        minJdate = stockdata_list[J_list.index(minJ)][0]
        return [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, stockdata_list[0][3], round(K_range,2), model_slope, K_list[0], D_list[0], J_list[0], RSV, minJ, minJdate, maxJ, maxJdate]
    else:
        return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
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
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
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
    EMA1 = 0
    EMA2 = 0
    EMA1_list = []
    EMA2_list = []
    DIFF_list = [0]
    DEA_list = [0]
    DEAratio_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(perioddaynum)):
        EMA1 = (N1-1)/(N1+1)*EMA1 + 2/(N1+1)*closingprice_list[ii]
        EMA2= (N2-1)/(N2+1)*EMA2 + 2/(N2+1)*closingprice_list[ii]
        DIFF = EMA1 - EMA2
        DEA = (N3-1)/(N3+1)*DEA_list[0] + 2/(N3+1)*DIFF
        DEAratio = DEA/closingprice_list[ii]
        MACD = (DIFF-DEA)*2
        EMA1_list.insert(0, EMA1)
        EMA2_list.insert(0, EMA2)
        DIFF_list.insert(0, DIFF)
        DEA_list.insert(0, DEA)
        DEAratio_list.insert(0, DEAratio)
        MACD_list.insert(0, MACD)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(MACD_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (closingprice/closingprice_list[model_counter]-1)*100
        model_predict = math.ceil(MACD_list[0]/(MACD_list[1]-MACD_list[0]))
        model_slope = (MACD_list[0]-MACD_list[1])/closingprice
# Solve Function (DIFF(new)-DEA(new))*2 = MACD (i.e. 0, MACD_list[0], 2*MACD_list[0]-MACD_list[1])
# DIFF(new)-((N3-1)/(N3+1)*DEA_list[0]+2/(N3+1)*DIFF(new)) = MACD/2
# (N3-1)/(N3+1)*(DIFF(new)*DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(EMA1(new)-EMA2(new)-DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0]) = MACD/2
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0] = MACD/2*(N3+1)/(N3-1)
# x =  (MACD/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_price = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_range = (cross_price/closingprice-1)*100
        trend_price = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trend_range = (trend_price/closingprice-1)*100
        parallel_price = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallel_range = (parallel_price/closingprice-1)*100
        DEA = min(DEA_list[:model_counter])
        minDEA = min(DEA_list[:min(100, perioddaynum)])
        minDEAdate = stockdata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][0]
        DEAratio = min(DEAratio_list[:model_counter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = stockdata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][0]
        MACD_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, DEA, DEAratio, model_range, model_slope, round(cross_range,2), round(trend_range,2), round(parallel_range,2), minDEA, minDEAdate, minDEAratio, minDEAratiodate]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(DIFF_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (closingprice/closingprice_list[model_counter]-1)*100
        model_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        model_slope = (DIFF_list[0]-DIFF_list[1])/closingprice
# Solve Function DIFF(new) = DIFF (i.e. 0, DIFF_list[0], 2*DIFF_list[0]-DIFF_list[1])
# EMA1(new)-EMA2(new) = DIFF
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x) = DIFF
# x = (DIFF+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_price = ((N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_range = (cross_price/closingprice-1)*100
        trend_price = ((2*DIFF_list[0]-DIFF_list[1])+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trend_range = (trend_price/closingprice-1)*100
        parallel_price = (DIFF_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallel_range = (parallel_price/closingprice-1)*100
        DEA = min(DEA_list[:model_counter])
        minDEA = min(DEA_list[:min(100, perioddaynum)])
        minDEAdate = stockdata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][0]
        DEAratio = min(DEAratio_list[:model_counter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = stockdata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][0]
        DIFF_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, model_slope, DEA, DEAratio, round(cross_range,2), round(trend_range,2), round(parallel_range,2), minDEA, minDEAdate, minDEAratio, minDEAratiodate]
    return MACD_result, DIFF_result


def EMV_Model_Select():
# EMV 模型 (40,16) & 移动平均 EMVDIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "EMVDIFF_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "EMV_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算EMVDIFF金叉天数", "EMVDIFF下方天数", "上穿前总跌幅", "EMV", "EMV比例", "EMV斜率", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV","EMV比例", "EMV斜率", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
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
    title1 = ["股票名称", "当日涨跌幅", "估算EMVDIFF金叉天数", "EMVDIFF下方天数", "上穿前总跌幅", "EMV", "EMV比例", "EMV斜率", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV","EMV比例", "EMV斜率", "百日最低EMV", "日期", "百日最低相对EMV比例", "日期"]
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
    perioddaynum = min(400, len(stockdata_list)-1)
    if(perioddaynum<200):
        return [], []
    EMV_result = []
    EMVMACD_result = []
    EMV_list = [0]
    EMVratio_list = [0]
    MAEMV_list = [0]
    EMVDIFF_list = [0]
    for ii in reversed(range(perioddaynum)):
        MID = (float(stockdata_list[ii][3])+float(stockdata_list[ii][4])+float(stockdata_list[ii][5]))/3 - (float(stockdata_list[ii+1][3])+float(stockdata_list[ii+1][4])+float(stockdata_list[ii+1][5]))/3
        BRO = float(stockdata_list[ii][4])-float(stockdata_list[ii][5])
        EM = MID*BRO/float(stockdata_list[ii][10])
        EMV = EMV_list[0]*(N1-1)/(N1+1) + EM*2/(N1+1)
        EMVratio = EMV*float(stockdata_list[ii][10])/(float(stockdata_list[ii][3])**2)
        MAEMV = MAEMV_list[0]*(N2-1)/(N2+1) + EMV*2/(N2+1)
        EMVDIFF = EMV-MAEMV
        EMV_list.insert(0, EMV)
        EMVratio_list.insert(0, EMVratio)
        MAEMV_list.insert(0, MAEMV)
        EMVDIFF_list.insert(0, EMVDIFF)
    if((EMV_list[0]<0) and (EMVDIFF_list[1]<0) and (EMVDIFF_list[0]>EMVDIFF_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(EMVDIFF_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (float(stockdata_list[0][3])-float(stockdata_list[model_counter][3]))/float(stockdata_list[model_counter][3])*100
        model_predict = math.ceil(EMVDIFF_list[0]/(EMVDIFF_list[1]-EMVDIFF_list[0]))
        model_slope = (EMV_list[0]-EMV_list[1])*float(stockdata_list[0][10])/(float(stockdata_list[0][3])**2)
        minEMV = min(EMV_list[:min(100, perioddaynum)])
        minEMVdate = stockdata_list[EMV_list[:min(100, perioddaynum)].index(minEMV)][0]
        minEMVratio = min(EMVratio_list[:min(100, perioddaynum)])
        minEMVratiodate = stockdata_list[EMVratio_list[:min(100, perioddaynum)].index(minEMVratio)][0]
        EMVMACD_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, EMV_list[0], EMVratio_list[0], model_slope, minEMV, minEMVdate, minEMVratio, minEMVratiodate]
    if((EMV_list[1]<0) and (EMV_list[0]>EMV_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(EMV_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (float(stockdata_list[0][3])-float(stockdata_list[model_counter][3]))/float(stockdata_list[model_counter][3])*100
        model_predict = math.ceil(EMV_list[0]/(EMV_list[1]-EMV_list[0]))
        model_slope = (EMV_list[0]-EMV_list[1])*float(stockdata_list[0][10])/(float(stockdata_list[0][3])**2)
        minEMV = min(EMV_list[:min(100, perioddaynum)])
        minEMVdate = stockdata_list[EMV_list[:min(100, perioddaynum)].index(minEMV)][0]
        minEMVratio = min(EMVratio_list[:min(100, perioddaynum)])
        minEMVratiodate = stockdata_list[EMVratio_list.index(minEMVratio)][0]
        EMV_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, EMV_list[0], EMVratio_list[0], model_slope, minEMV, minEMVdate, minEMVratio, minEMVratiodate]
    return EMVMACD_result, EMV_result


def DMI_Model_Select():
# DMI 模型 & ADX 模型
    resultfile_path1 = os.path.join(resultdata_path, "DMI_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "ADX_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "PDI", "MDI", "ADX", "DMI斜率"]
    title2 = ["股票名称", "当日涨跌幅", "ADX趋势天数", "趋势涨跌幅", "PDI", "MDI", "ADX", "DMI斜率"]
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
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "PDI", "MDI", "ADX", "DMI斜率"]
    title2 = ["股票名称", "当日涨跌幅", "ADX趋势天数", "趋势涨跌幅", "PDI", "MDI", "ADX", "DMI斜率"]
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
    perioddaynum = min(400, len(stockdata_list)-N1-1)
    if(perioddaynum<200):
        return [], []
    DMI_result = []
    ADX_result = []
    PDM_list = []
    MDM_list = []
    TR_list = []
    DX_list = []
    PDI_list = []
    MDI_list = []
    DMI_list = []
    MADX_list = []
    for ii in range(perioddaynum+N1):
        TR = max(abs(float(stockdata_list[ii][4])-float(stockdata_list[ii][5])), abs(float(stockdata_list[ii][4])-float(stockdata_list[ii+1][3])), abs(float(stockdata_list[ii+1][3])-float(stockdata_list[ii][5])))
        PDM = max((float(stockdata_list[ii][4])-float(stockdata_list[ii+1][4])), 0)
        MDM = max((float(stockdata_list[ii+1][5])-float(stockdata_list[ii][5])), 0)
        if(PDM>MDM):
            MDM = 0
        elif(MDM>PDM):
            PDM = 0
        else:
            MDM = 0
            PDM = 0
        PDM_list.append(PDM)
        MDM_list.append(MDM)
        TR_list.append(TR)
    for ii in reversed(range(perioddaynum)):
        PDM = sum(PDM_list[ii:ii+N1])
        MDM = sum(MDM_list[ii:ii+N1])
        TR = sum(TR_list[ii:ii+N1])
        PDI = (PDM/TR)*100
        MDI = (MDM/TR)*100
        DMI = PDI - MDI
        DX = abs(PDI-MDI)/(PDI+MDI)*100
        PDI_list.insert(0, PDI)
        MDI_list.insert(0, MDI)
        DMI_list.insert(0, DMI)
        DX_list.insert(0, DX)
        MADX = np.mean(DX_list[:N2])
        MADX_list.insert(0, MADX)
    if((DMI_list[1]<0) and (DMI_list[0]>DMI_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(DMI_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (closingprice-float(stockdata_list[model_counter-1][3]))/float(stockdata_list[model_counter-1][3])*100
        model_predict = math.ceil(DMI_list[0]/(DMI_list[1]-DMI_list[0]))
        model_slope = (DMI_list[0]-DMI_list[1])
        DMI_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, PDI_list[0], MDI_list[0], MADX_list[0], model_slope]
    if((MADX_list[1]<MADX_list[2]) and (MADX_list[1]<MADX_list[0])):
        model_counter = 1
        for ii in range(1, perioddaynum-1):
            if(MADX_list[ii]<MADX_list[ii+1]):
                model_counter += 1
            else:
                break
        model_range = (closingprice-float(stockdata_list[model_counter][3]))/float(stockdata_list[model_counter-1][3])*100
        model_slope = (DMI_list[0]-DMI_list[1])
        ADX_result = [stockinfo, stockdata_list[0][9], model_counter, model_range, PDI_list[0], MDI_list[0], MADX_list[0], model_slope]
    if((MADX_list[1]>MADX_list[2]) and (MADX_list[1]>MADX_list[0])):
        model_counter = 1
        for ii in range(1, perioddaynum-1):
            if(MADX_list[ii]>MADX_list[ii+1]):
                model_counter += 1
            else:
                break
        model_range = (closingprice-float(stockdata_list[model_counter][3]))/float(stockdata_list[model_counter-1][3])*100
        model_slope = (DMI_list[0]-DMI_list[1])
        ADX_result = [stockinfo, stockdata_list[0][9], model_counter, model_range, PDI_list[0], MDI_list[0], MADX_list[0], model_slope]
    return DMI_result, ADX_result


def obv_Model_Select():
# OBV模型+多空净额比率法修正+MACD 模型 & DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "obvMACD斜率", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "obvDIFF斜率", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        OBVMACD_result, OBVDIFF_result = obv_Model_Select_pipeline(filename)
        resultdata_list1.append(OBVMACD_result)
        resultdata_list2.append(OBVDIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def obv_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "obvMACD斜率", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "obvDIFF斜率", "当日obvDEA比例", "百日最小obvDEA比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obv_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def obv_Model_Select_pipeline(filename):
    N1 = 12
    N2 = 26
    N3 = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(400, len(stockdata_list)-1)
    if(perioddaynum<200):
        return [], []
    OBVMACD_result = []
    OBVDIFF_result = []
    OBVEMA1 = 0
    OBVEMA2 = 0
    OBV_list = [0]
    OBVEMA1_list = []
    OBVEMA2_list = []
    OBVDIFF_list = [0]
    OBVDEA_list = [0]
    OBVDEAratio_list = [0]
    OBVMACD_list = [0]
    for ii in reversed(range(perioddaynum)):
        OBV = float(stockdata_list[ii][10])
        OBVEMA1 = (N1-1)/(N1+1)*OBVEMA1 + 2/(N1+1)*OBV
        OBVEMA2 = (N2-1)/(N2+1)*OBVEMA2 + 2/(N2+1)*OBV
        OBVDIFF = OBVEMA1 - OBVEMA2
        OBVDEA = (N3-1)/(N3+1)*OBVDEA_list[0] + 2/(N3+1)*OBVDIFF
        OBVDEAratio = OBVDEA/OBV
        OBVMACD = (OBVDIFF-OBVDEA)*2
        OBV_list.insert(0, OBV)
        OBVDIFF_list.insert(0, OBVDIFF)
        OBVDEA_list.insert(0, OBVDEA)
        OBVDEAratio_list.insert(0, OBVDEAratio)
        OBVMACD_list.insert(0, OBVMACD)
    if((OBVMACD_list[1]<0) and (OBVMACD_list[0]>OBVMACD_list[1]) and (OBVDEA_list[1]<0)):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(OBVMACD_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (closingprice/float(stockdata_list[model_counter][3])-1)*100
        model_predict = math.ceil(OBVMACD_list[0]/(OBVMACD_list[1]-OBVMACD_list[0]))
        model_slope = (OBVMACD_list[0]-OBVMACD_list[1])/OBV_list[0]
        OBVDEAratio = min(OBVDEAratio_list[:model_counter])
        minOBVDEAratio = min(OBVDEAratio_list[:min(100, perioddaynum)])
        minOBVDEAratiodate = stockdata_list[OBVDEAratio_list[:min(100, perioddaynum)].index(minOBVDEAratio)][0]
        OBVMACD_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, model_slope, OBVDEAratio, minOBVDEAratio, minOBVDEAratiodate]
    if((OBVDIFF_list[1]<0) and (OBVDIFF_list[0]>OBVDIFF_list[1])):
        model_counter = 1
        for ii in range(1, perioddaynum):
            if(OBVDIFF_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (closingprice/float(stockdata_list[model_counter][3])-1)*100
        model_predict = math.ceil(OBVDIFF_list[0]/(OBVDIFF_list[1]-OBVDIFF_list[0]))
        model_slope = (OBVDIFF_list[0]-OBVDIFF_list[1])/OBV_list[0]
        OBVDEAratio = min(OBVDEAratio_list[:model_counter])
        minOBVDEAratio = min(OBVDEAratio_list[:min(100, perioddaynum)])
        minOBVDEAratiodate = stockdata_list[OBVDEAratio_list[:min(100, perioddaynum)].index(minOBVDEAratio)][0]
        OBVDIFF_predict = math.ceil(OBVDIFF_list[0]/(OBVDIFF_list[1]-OBVDIFF_list[0]))
        OBVDIFF_result = [stockinfo, stockdata_list[0][9], model_predict, model_counter, model_range, model_slope, OBVDEAratio, minOBVDEAratio, minOBVDEAratiodate]
    return OBVMACD_result, OBVDIFF_result


def similar_Model_Select():
# K 线相似度比较
    resultfile_path = os.path.join(resultdata_path, "similar_Model_Select_Result.csv")
    title = ["股票名称", "当前股票最大相似度", "当前未来五日涨跌幅", "当前相似日期", "所有股票最大相似度", "所有未来五日涨跌幅", "相似股票名称", "相似日期", "当前未来1日预测", "当前未来2日预测", "当前未来3日预测", "当前未来4日预测", "当前未来5日预测", "所有未来1日预测", "所有未来2日预测", "所有未来3日预测", "所有未来4日预测", "所有未来5日预测"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(similar_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def similar_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "similar_Model_Select_Result.csv")
    title = ["股票名称", "当前股票最大相似度", "当前未来五日涨跌幅", "当前相似日期", "所有股票最大相似度", "所有未来五日涨跌幅", "相似股票名称", "相似日期", "当前未来1日预测", "当前未来2日预测", "当前未来3日预测", "当前未来4日预测", "当前未来5日预测", "所有未来1日预测", "所有未来2日预测", "所有未来3日预测", "所有未来4日预测", "所有未来5日预测"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(similar_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def similar_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    selfsimidate = ""
    if(len(stockdata_list)<100):
        return []
    ref_list = [float(item[3]) for item in stockdata_list[:30]]
    maxselfsimidegree = 0
    selfprerange = 0
    selfprerange_list = [0, 0, 0, 0, 0]
    for ii in range(75, min(125, len(stockdata_list)-30)):
        closingprice_list = [float(item[3]) for item in stockdata_list[ii:(ii+30)]]
        simidegree, _ = pearsonr(closingprice_list,ref_list)
        if(simidegree>maxselfsimidegree):
            maxselfsimidegree = simidegree
            selfsimidate = stockdata_list[ii][0]
            selfprerange_list = list(reversed([float(item[9]) for item in stockdata_list[(ii-5):ii]]))
            selfprerange = sum(selfprerange_list)
    maxallsimidegree = 0
    allprerange = 0
    allprerange_list = [0, 0, 0, 0, 0]
    allsimidate = ""
    simistockinfo = ""
    filename2_list = os.listdir(stockdata_path)
    filename2_list.remove(filename)
    for filename2 in filename2_list:
        if(filename2.split('-')[0]!=filename.split('-')[0]):
            continue
        _, stockdata2_list = read_csvfile(os.path.join(stockdata_path, filename2))
        if(len(stockdata2_list)<100):
            continue
        for ii in range(5, 10):
            closingprice_list = [float(item[3]) for item in stockdata2_list[ii:(ii+30)]]
            simidegree, _ = pearsonr(closingprice_list, ref_list)
            if(simidegree>maxallsimidegree):
                maxallsimidegree = simidegree
                simistockinfo = filename2.split(".")[0]
                allsimidate = stockdata2_list[ii][0]
                allprerange_list = list(reversed([float(item[9]) for item in stockdata2_list[(ii-5):ii]])) 
                allprerange = sum(allprerange_list)
    return [stockinfo, maxselfsimidegree, selfprerange, selfsimidate, maxallsimidegree, allprerange, simistockinfo, allsimidate] + selfprerange_list + allprerange_list


def lagging_calc(comdata_list, perioddaynum):
    perioddaynum = min(perioddaynum, len(comdata_list)-1)
    lagging_counter = 0
    for ii in range(perioddaynum):
        if(float(comdata_list[ii][2])<float(comdata_list[ii][4])):
            lagging_counter += 1
    lagging_range = (float(comdata_list[0][3])-float(comdata_list[perioddaynum][3]))/float(comdata_list[perioddaynum][3])*100 - (float(comdata_list[0][1])-float(comdata_list[perioddaynum][1]))/float(comdata_list[perioddaynum][1])*100
    return lagging_counter, lagging_range


def lagging_Model_Select():
# 与指数 相比滞后幅度
    index_list = ["上证指数_0000001", "深证成指_1399001"]
    indexfile_list = [os.path.join(indexdata_path, (item+".csv")) for item in index_list]
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(lagging_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
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
            comdata_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], indexdata_list[offset2][3], 0])
            offset1+=1
        elif(stockdata_list[offset1][0]<indexdata_list[offset2][0]):
            comdata_list.append([indexdata_list[offset2][0], stockdata_list[offset1][3], 0, indexdata_list[offset2][3], indexdata_list[offset2][9]])
            offset2+=1
        else:
            comdata_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], indexdata_list[offset2][3], indexdata_list[offset2][9]])
            offset1+=1
            offset2+=1
        if(offset1==min(510,len(stockdata_list))):
            break
        if(offset2==min(510,len(indexdata_list))):
            break
    lagging_counter = 0
    for ii in range(len(comdata_list)):
        if(float(comdata_list[ii][2])<float(comdata_list[ii][4])):
            lagging_counter += 1
        else:
            break
    stock_range = (float(comdata_list[0][1])/float(comdata_list[lagging_counter][1])-1)*100
    com_range = (float(comdata_list[0][3])/float(comdata_list[lagging_counter][3])-1)*100
    lagging_range = com_range - stock_range
    lagging30_counter, lagging30_range = lagging_calc(comdata_list, 30)
    lagging60_counter, lagging60_range = lagging_calc(comdata_list, 60)
    lagging100_counter, lagging100_range = lagging_calc(comdata_list, 100)
    lagging200_counter, lagging200_range = lagging_calc(comdata_list, 200)
    lagging500_counter, lagging500_range = lagging_calc(comdata_list, 500)
    maxlagging_counter = 0
    maxlagging_range = 0
    for ii in range(lagging_counter, min(100, len(comdata_list)-1)):
        templagging_counter = 0
        templagging_range = 0
        for jj in range(ii, min(100, len(comdata_list)-1)):
            if(float(comdata_list[jj][2])<float(comdata_list[jj][4])):
                templagging_counter += 1
            else:
                break
            templagging_range = (float(comdata_list[ii][3])/float(comdata_list[ii+templagging_counter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templagging_counter][1])-1)*100
            if(maxlagging_range<templagging_range):
                maxlagging_range=templagging_range
            if(maxlagging_counter<templagging_counter):
                maxlagging_counter=templagging_counter
    return [stockinfo, comdata_list[0][2], stock_range, com_range, lagging_range, lagging_counter, maxlagging_range, maxlagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter]
    

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
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], HKdata_list[offset2][1], 0])
                            offset1+=1
                        elif(CNdata_list[offset1][0]<HKdata_list[offset2][0]):
                            comdata_list.append([HKdata_list[offset2][0], CNdata_list[offset1][3], 0, HKdata_list[offset2][1], HKdata_list[offset2][6]])
                            offset2+=1
                        else:
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], HKdata_list[offset2][1], HKdata_list[offset2][6]])
                            offset1+=1
                            offset2+=1
                        if(offset1==min(510,len(CNdata_list))):
                            break
                        if(offset2==min(510,len(HKdata_list))):
                            break
                    lagging_counter = 0
                    for jj in range(len(comdata_list)):
                        if(float(comdata_list[jj][2])<float(comdata_list[jj][4])):
                            lagging_counter += 1
                        else:
                            break
                    stock_range = (float(comdata_list[0][1])-float(comdata_list[lagging_counter][1]))/float(comdata_list[lagging_counter][1])*100
                    com_range = (float(comdata_list[0][3])-float(comdata_list[lagging_counter][3]))/float(comdata_list[lagging_counter][3])*100
                    lagging_range = com_range - stock_range
                    lagging30_counter, lagging30_range = lagging_calc(comdata_list, 30)
                    lagging60_counter, lagging60_range = lagging_calc(comdata_list, 60)
                    lagging100_counter, lagging100_range = lagging_calc(comdata_list, 100)
                    lagging200_counter, lagging200_range = lagging_calc(comdata_list, 200)
                    lagging500_counter, lagging500_range = lagging_calc(comdata_list, 500)
                    maxlagging_counter = 0
                    maxlagging_range = 0
                    stock_range = (float(comdata_list[0][1])/float(comdata_list[lagging_counter][1])-1)*100
                    com_range = (float(comdata_list[0][3])/float(comdata_list[lagging_counter][3])-1)*100
                    lagging_range = com_range - stock_range
                    lagging30_counter, lagging30_range = lagging_calc(comdata_list, 30)
                    lagging60_counter, lagging60_range = lagging_calc(comdata_list, 60)
                    lagging100_counter, lagging100_range = lagging_calc(comdata_list, 100)
                    lagging200_counter, lagging200_range = lagging_calc(comdata_list, 200)
                    lagging500_counter, lagging500_range = lagging_calc(comdata_list, 500)
                    maxlagging_counter = 0
                    maxlagging_range = 0
                    for ii in range(lagging_counter, min(100, len(comdata_list)-1)):
                        templagging_counter = 0
                        templagging_range = 0
                        for jj in range(ii, min(100, len(comdata_list)-1)):
                            if(float(comdata_list[jj][2])<float(comdata_list[jj][4])):
                                templagging_counter += 1
                            else:
                                break
                            templagging_range = (float(comdata_list[ii][3])/float(comdata_list[ii+templagging_counter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templagging_counter][1])-1)*100
                            if(maxlagging_range<templagging_range):
                                maxlagging_range=templagging_range
                            if(maxlagging_counter<templagging_counter):
                                maxlagging_counter=templagging_counter
                    resultdata_list.append([stockinfo, A_Hratio, stock_range, com_range, lagging_range, lagging_counter, maxlagging_range, maxlagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter])
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
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], Bdata_list[offset2][3], 0])
                            offset1+=1
                        elif(CNdata_list[offset1][0]<Bdata_list[offset2][0]):
                            comdata_list.append([Bdata_list[offset2][0], CNdata_list[offset1][3], 0, Bdata_list[offset2][3], Bdata_list[offset2][9]])
                            offset2+=1
                        else:
                            comdata_list.append([CNdata_list[offset1][0], CNdata_list[offset1][3], CNdata_list[offset1][9], Bdata_list[offset2][3], Bdata_list[offset2][9]])
                            offset1+=1
                            offset2+=1
                        if(offset1==min(510, len(CNdata_list))):
                            break
                        if(offset2==min(510, len(Bdata_list))):
                            break
                    lagging_counter = 0
                    for jj in range(len(comdata_list)):
                        if(float(comdata_list[jj][2])<float(comdata_list[jj][4])):
                            lagging_counter += 1
                        else:
                            break
                    stock_range = (float(comdata_list[0][1])-float(comdata_list[lagging_counter][1]))/float(comdata_list[lagging_counter][1])*100
                    com_range = (float(comdata_list[0][3])-float(comdata_list[lagging_counter][3]))/float(comdata_list[lagging_counter][3])*100
                    lagging_range = com_range - stock_range 
                    lagging30_counter, lagging30_range = lagging_calc(comdata_list, 30)
                    lagging60_counter, lagging60_range = lagging_calc(comdata_list, 60)
                    lagging100_counter, lagging100_range = lagging_calc(comdata_list, 100)
                    lagging200_counter, lagging200_range = lagging_calc(comdata_list, 200)
                    lagging500_counter, lagging500_range = lagging_calc(comdata_list, 500)
                    maxlagging_counter = 0
                    maxlagging_range = 0
                    for ii in range(lagging_counter, min(100, len(comdata_list)-1)):
                        templagging_counter = 0
                        templagging_range = 0
                        for jj in range(ii, min(100, len(comdata_list)-1)):
                            if(float(comdata_list[jj][2])<float(comdata_list[jj][4])):
                                templagging_counter += 1
                            else:
                                break
                            templagging_range = (float(comdata_list[ii][3])/float(comdata_list[ii+templagging_counter][3])-1)*100-(float(comdata_list[ii][1])/float(comdata_list[ii+templagging_counter][1])-1)*100
                            if(maxlagging_range<templagging_range):
                                maxlagging_range=templagging_range
                            if(maxlagging_counter<templagging_counter):
                                maxlagging_counter=templagging_counter
                    resultdata_list.append([stockinfo, A_Bratio, stock_range, com_range, lagging_range, lagging_counter, maxlagging_range, maxlagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter])
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
                    margin_df = tspro.margin_detail(ts_code=gen_tscode(marginData_list[ii][0][-6:]), start_date=start_time, end_date=end_time)
                    margin_df = margin_df[["trade_date", "ts_code", "rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye"]]
                    margin_list = margin_df.values.tolist()
                    for jj in reversed(range(len(margin_list))):
                        if(np.isnan(margin_list[jj][2:]).any()):
                            margin_list.pop(jj)
                        else:
                            margin_list[jj][0] = margin_list[jj][0][0:4]+'-'+margin_list[jj][0][4:6]+'-'+margin_list[jj][0][6:8]
                    write_csvfile(os.path.join(margindata_path, marginData_list[ii][0]+'.csv'), margin_title, margin_list)
                    time.sleep(1)
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
                    rzjye_list = [(float(margin_list[ii][2])-float(margin_list[ii][3])) for ii in range(perioddaynum)]
                    rzjye_range = ((rzjye_list[0]/rzjye_list[1])-1)*100
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
                        resultdata_list.append([stockinfo, rzjye_range, rzjye_list[0], rzjyereboundrange, pricereboundrange, rzjyereboundcounter, rzjyefailrange, pricefailrange, rzjyefailcounter,
                        	                     lastrzjyereboundrange, lastpricereboundrange, lastrzjyereboundcounter, lastrzjyefailrange, lastpricefailrange, lastrzjyefailcounter])
        write_csvfile(resultfile_path, title, resultdata_list)


def blockTrade_Model_Select():
# 大宗交易数据
    resultfile_path = os.path.join(resultdata_path, "blockTrade_Model_Select_Result.csv")
    title = ["股票名称", "交易日历", "交易价格", "交易溢价率", "成交量(万股)", "交易换手率", "当日换手率", "成交金额", "买方营业部", "卖方营业部"]
    resultdata_list = []
    for ii in range(3):
        try:
            df_blockTrade = tspro.block_trade(start_date=start_time, end_date=end_time)
        except Exception as e:
            time.sleep(600)
            print(e)
    for item in df_blockTrade.values:
        if((item[0][:3]!="300") and (item[-2][:4]!=item[-1][:4])):
            item_list = list(item)
            for filename in os.listdir(stockdata_path):
                if(item_list[0][:6]==filename.split(".")[0][-6:]):
                    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    item_list[0] = filename.split(".")[0]
                    closingprice = stockdata_list[0][3]
                    convpre = (float(item_list[2])/float(closingprice)-1)*100
                    item_list.insert(3, convpre)
                    item_list.insert(5, float(stockdata_list[0][10])*float(item_list[4])*10000/float(stockdata_list[0][11]))
                    item_list.insert(6, stockdata_list[0][10])
                    resultdata_list.append(item_list)
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
    monthmaxprice_list = [max([float(stockdata_list[jj][4]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    monthminprice_list = [min([float(stockdata_list[jj][5]) for jj in range(monthoffset_list[ii],monthoffset_list[ii+1])]) for ii in range(len(monthoffset_list)-1)]
    return monthclosingprice_list, monthmaxprice_list, monthminprice_list


def dropMonth_Model_Select():
# 月连续跌幅
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "连续跌幅月数", "月累计总跌幅", "最多连续跌幅月数", "最大月连续跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(dropMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "dropMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "连续跌幅月数", "月累计总跌幅", "最多连续跌幅月数", "最大月连续跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(dropMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def dropMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    if(len(monthclosingprice_list)<5):
        return []
    month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
    monthdropcounter = 0
    for ii in range(1, len(monthclosingprice_list)-1):
        if(monthclosingprice_list[ii]<=monthclosingprice_list[ii+1]):
            monthdropcounter += 1
        else:
            break
    if(monthdropcounter>0):
        monthdroprange = (monthclosingprice_list[1]-monthclosingprice_list[monthdropcounter+1])/monthclosingprice_list[monthdropcounter+1]*100
        maxdropcounter = 0
        maxdroprange = 0
        for ii in range(monthdropcounter, len(monthclosingprice_list)):
            tempdropcounter = 0
            for jj in range(ii, len(monthclosingprice_list)-1):
                if(monthclosingprice_list[jj]<=monthclosingprice_list[jj+1]):
                    tempdropcounter += 1
                else:
                    tempdroprange = (monthclosingprice_list[ii]-monthclosingprice_list[ii+tempdropcounter])/monthclosingprice_list[ii+tempdropcounter]*100
                    if(tempdroprange<maxdroprange):
                        maxdroprange = tempdroprange
                    if(tempdropcounter>maxdropcounter):
                        maxdropcounter = tempdropcounter
                    break
        return [stockinfo, month_range, monthdropcounter, monthdroprange, maxdropcounter, maxdroprange]
    else:
        return []


def KDJMonth_Model_Select():
# 月 KDJ 模型
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "预测交叉涨跌幅", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "预测交叉涨跌幅", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_pipeline(filename):
    N = 9
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = 20
    if(len(monthclosingprice_list)-N<periodmonthnum):
        return []
    K_list = [50]
    D_list = [50]
    J_list = [50]
    DIFF_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(periodmonthnum)):
        C9 = monthclosingprice_list[ii]
        H9 = max(monthmaxprice_list[ii:ii+9])
        L9 = min(monthminprice_list[ii:ii+9])
        RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[0]+1/3*RSV
        D = 2/3*D_list[0]+1/3*K
        J = 3*K-2*D
        K_list.insert(0, K)
        D_list.insert(0, D)
        J_list.insert(0, J)
        DIFF_list.insert(0, K-D)
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (monthclosingprice_list[0]/monthclosingprice_list[model_counter-1]-1)*100
        model_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        model_slope = (DIFF_list[0]-DIFF_list[1])/monthclosingprice_list[0]
        K_price = (H9-L9)*K_list[0]/100+L9
        K_range = (K_price/monthclosingprice_list[0]-1)*100
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, round(model_predict,2), model_counter, round(model_range,2), round(K_range,2), model_slope, K_list[0], D_list[0], J_list[0], RSV]
    else:
        return []


def MACDDIFFMonth_Model_Select():
# MACD 模型 (12,26,9)
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅"]
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DEA比例", "上穿前总跌幅", "DIFF斜率", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅"]
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
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅"]
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DEA比例", "上穿前总跌幅", "DIFF斜率", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅"]
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
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = 36
    if(len(monthclosingprice_list)-1<periodmonthnum):
        return [], []
    EMA1 = 0
    EMA2 = 0
    EMA1_list = []
    EMA2_list = []
    DIFF_list = [0]
    DEA_list = [0]
    DEAratio_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in range(periodmonthnum):
        EMA1 = (N1-1)/(N1+1)*EMA1 + 2/(N1+1)*monthclosingprice_list[ii]
        EMA2 = (N2-1)/(N2+1)*EMA2 + 2/(N2+1)*monthclosingprice_list[ii]
        DIFF = EMA1 - EMA2
        DEA = (N3-1)/(N3+1)*DEA_list[0] + 2/(N3+1)*DIFF
        DEAratio = DEA/monthclosingprice_list[ii]
        MACD = (DIFF-DEA)*2
        EMA1_list.insert(0, EMA1)
        EMA2_list.insert(0, EMA2)
        DIFF_list.insert(0, DIFF)
        DEA_list.insert(0, DEA)
        DEAratio_list.insert(0, DEAratio)
        MACD_list.insert(0, MACD)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        model_counter = 1
        for ii in range(1, periodmonthnum):
            if(MACD_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (monthclosingprice_list[0]/monthclosingprice_list[model_counter]-1)*100
        model_predict = MACD_list[0]/(MACD_list[1]-MACD_list[0])
        model_slope = (MACD_list[0]-MACD_list[1])/monthclosingprice_list[0]
# Solve Function (DIFF(new)-DEA(new))*2 = MACD (i.e. 0, MACD_list[0], 2*MACD_list[0]-MACD_list[1])
# DIFF(new)-((N3-1)/(N3+1)*DEA_list[0]+2/(N3+1)*DIFF(new)) = MACD/2
# (N3-1)/(N3+1)*(DIFF(new)*DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(EMA1(new)-EMA2(new)-DEA_list[0]) = MACD/2
# (N3-1)/(N3+1)*(((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0]) = MACD/2
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x)-DEA_list[0] = MACD/2*(N3+1)/(N3-1)
# x =  (MACD/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_price = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_range = (cross_price/monthclosingprice_list[0]-1)*100
        trend_price = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trend_range = (trend_price/monthclosingprice_list[0]-1)*100
        parallel_price = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallel_range = (parallel_price/monthclosingprice_list[0]-1)*100
        DEAratio = min(DEAratio_list[:model_counter])
        month_range = (monthclosingprice/monthclosingprice_list[0]-1)*100
        MACD_result = [stockinfo, month_range, round(model_predict,2), model_counter, DEAratio, model_range, model_slope, round(cross_range,2), round(trend_range,2), round(parallel_range,2)]
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                model_counter+=1
            else:
                break
        model_range = (monthclosingprice_list[0]/monthclosingprice_list[model_counter]-1)*100
        model_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        model_slope = (DIFF_list[0]-DIFF_list[1])/monthclosingprice_list[0]
# Solve Function DIFF(new) = DIFF (i.e. 0, DIFF_list[0], 2*DIFF_list[0]-DIFF_list[1])
# EMA1(new)-EMA2(new) = DIFF
# ((N1-1)/(N1+1)*EMA1_list[0]+2/(N1+1)*x)-((N2-1)/(N2+1)*EMA2_list[0]+2/(N2+1)*x) = DIFF
# x = (DIFF+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_price = ((N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_range = (cross_price/monthclosingprice_list[0]-1)*100
        trend_price = ((2*DIFF_list[0]-DIFF_list[1])+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trend_range = (trend_price/monthclosingprice_list[0]-1)*100
        parallel_price = (DIFF_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallel_range = (parallel_price/monthclosingprice_list[0]-1)*100
        DEAratio = min(DEAratio_list[:model_counter])
        month_range = (monthclosingprice/monthclosingprice_list[0]-1)*100
        DIFF_result = [stockinfo, month_range, round(model_predict,2), model_counter, DEAratio, model_range, model_slope, round(cross_range,2), round(trend_range,2), round(parallel_range,2)]
    return MACD_result, DIFF_result


def trendMonth_Model_Select():
# K线图 1月线 贯穿 5月线  可拓展为 N1月线 贯穿 N2月线
    title = ["股票名称", "当月涨跌幅", "1月线上穿预测月数", "5月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "1月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "5月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10Month_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trendMonth_Model_Select_par():
    title = ["股票名称", "当月涨跌幅", "1月线上穿预测月数", "5月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "1月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
    title = ["股票名称", "当月涨跌幅", "5月线上穿预测月数", "10月线下方月数", "股票上穿前总跌幅", "月线交叉涨跌幅", "月线趋势涨跌幅", "月线平行涨跌幅"]
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
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    monthclosingprice = monthclosingprice_list[0]
    monthclosingprice_list = monthclosingprice_list[1:]
    periodmonthnum = 10
    if(len(monthclosingprice_list)-N2<periodmonthnum):
        return []
    MA1_list = []
    MA2_list = []
    DIFF_list = []
    for ii in range(periodmonthnum):
        MA1_list.append(np.mean(monthclosingprice_list[ii:ii+N1]))
        MA2_list.append(np.mean(monthclosingprice_list[ii:ii+N2]))
        DIFF_list.append(MA1_list[ii] - MA2_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        model_counter = 1
        for ii in range(1, periodmonthnum):
            if(DIFF_list[ii]<0):
                model_counter += 1
            else:
                break
        model_range = (monthclosingprice_list[0]/monthclosingprice_list[model_counter]-1)*100
        model_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
# Solve Function MA1(new)-MA2(new)=DIFF  (i.e. 0, DIFF_list[0], 2DIFF_list[0]-DIFF_list[1])
# (x+sum(monthclosingprice_list[:N1-1]))/N1 - (x+sum(monthclosingprice_list[:N2-1]))/N2 = DIFF 
# x = (DIFF+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        cross_price = (sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        cross_range = (cross_price/monthclosingprice_list[0]-1)*100
        trend_price = ((2*DIFF_list[0]-DIFF_list[1])+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trend_range = (trend_price/monthclosingprice_list[0]-1)*100
        parallel_price = (DIFF_list[0]+sum(monthclosingprice_list[:N2-1])/N2-sum(monthclosingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallel_range = (parallel_price/monthclosingprice_list[0]-1)*100
        month_range = (monthclosingprice/monthclosingprice_list[0]-1)*100
        return [stockinfo, month_range, round(model_predict,2), model_counter, model_range, round(cross_range,2), round(trend_range,2), round(parallel_range,2)]
    else:
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
    resultfile_list = os.listdir(resultdata_path)
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
    resultfile_list = os.listdir(resultdata_path)
    query_list = []
    for resultfile in resultfile_list:
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
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    selectfile_list = ["trend1T5_Model_Select_Result.csv", "trend5T10_Model_Select_Result.csv", "trend10T30_Model_Select_Result.csv", "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv",
    "DIFFLong_Model_Select_Result.csv", "MACDLong_Model_Select_Result.csv", "DIFFShort_Model_Select_Result.csv", "MACDShort_Model_Select_Result.csv",
     "KDJ_Model_Select_Result.csv", "DMI_Model_Select_Result.csv", "ADX_Model_Select_Result.csv", "EMV_Model_Select_Result.csv", "EMVMACD_Model_Select_Result.csv",
     "trend1T5Month_Model_Select_Result.csv", "trend5T10Month_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, selectfile_list[ii]))):
            selectfile_list.pop(ii)
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    resultdata_list = []
    for stockinfo in stockinfo_list:
        resultdata_list.append(summary_result_pipeline(stockinfo))
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_par():
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    selectfile_list = ["trend1T5_Model_Select_Result.csv", "trend1T10_Model_Select_Result.csv", "trend5T10_Model_Select_Result.csv", "trend10T30_Model_Select_Result.csv", "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv",
    "DIFFLong_Model_Select_Result.csv", "MACDLong_Model_Select_Result.csv", "DIFFShort_Model_Select_Result.csv", "MACDShort_Model_Select_Result.csv",
     "KDJ_Model_Select_Result.csv", "DMI_Model_Select_Result.csv", "ADX_Model_Select_Result.csv", "EMV_Model_Select_Result.csv", "EMVMACD_Model_Select_Result.csv",
     "trend1T5Month_Model_Select_Result.csv", "trend1T10Month_Model_Select_Result.csv", "trend5T10Month_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, selectfile_list[ii]))):
            selectfile_list.pop(ii)
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
    selectfile_list = ["trend1T5_Model_Select_Result.csv", "trend1T10_Model_Select_Result.csv", "trend5T10_Model_Select_Result.csv", "trend10T30_Model_Select_Result.csv",
    "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv", "MACDLong_Model_Select_Result.csv", "DIFFLong_Model_Select_Result.csv", "MACDShort_Model_Select_Result.csv", "DIFFShort_Model_Select_Result.csv",
     "KDJ_Model_Select_Result.csv", "DMI_Model_Select_Result.csv", "ADX_Model_Select_Result.csv", "EMV_Model_Select_Result.csv", "EMVMACD_Model_Select_Result.csv",
     "trend1T5Month_Model_Select_Result.csv", "trend1T10Month_Model_Select_Result.csv", "trend5T10Month_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
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
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Begin!")
#    drop_Model_Select()
    drop_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdrop_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trise_Model_Select Begin!")
#    rise_Model_Select()
    rise_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trise_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Begin!")
#    box_Model_Select()
    box_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tbox_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Begin!")
#    wave_Model_Select()
    wave_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVolumn_Model_Select Begin!")
#    volumn_Model_Select()
    volumn_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tVolumn_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Begin!")
#    trend_Model_Select()
    trend_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
#    MACDDIFF_Model_Select()
    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEMV_Model_Select Begin!")
#    EMV_Model_Select()
    EMV_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEMV_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDMI_Model_Select Begin!")
#    DMI_Model_Select()
    DMI_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tDMI_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Begin!")
#    KDJ_Model_Select()
    KDJ_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Begin!")
#    obv_Model_Select()
    obv_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tobv_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Begin!")
#    lagging_Model_Select()
    lagging_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tLagging_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Begin!")    
#    shadow_Model_Select()
    shadow_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tshadow_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Begin!")
#    dropMonth_Model_Select()
    dropMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tdropMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Begin!")    
#    vshape_Model_Select()
    vshape_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tvshape_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Begin!")    
#    KDJMonth_Model_Select()
    KDJMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Begin!")
#    MACDDIFFMonth_Model_Select()
    MACDDIFFMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFMonth_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Begin!")
#    trendMonth_Model_Select()
    trendMonth_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrendMonth_Model_Select Finished!")
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Begin!")
##    similar_Model_Select()
#    similar_Model_Select_par()
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Begin!")
    AHCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Begin!")
    ABCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblockTrade_Model_Select Begin!")
    blockTrade_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tblockTrade_Model_Select Finished!")
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
#    main()
    analyze_stockdata()