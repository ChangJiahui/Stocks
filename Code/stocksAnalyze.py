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
#stockgdzjc_path = os.path.join(root_path, "Data", "stock_gdzjc")
indexdata_path = os.path.join(root_path, "Data", "index_data")
HKdata_path = os.path.join(root_path, "Data", "stockHK_data")
Bdata_path = os.path.join(root_path, "Data", "stockB_data")
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
    return Fals


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
    df = tspro.trade_cal(exchange='', start_date=end_time, end_date=end_time)
    df_list = df.values.tolist()
    if(df_list[0][2]==1):
        return True
    else:
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
    title = ["股票名称", "当日涨跌幅", "百日位置(%)", "总交易日", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "10日标准差", "20日标准差", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅", "平均20日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
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
    except Exception as e:
        print(e)
    for ii in range(len(resultdata_list)):
        time.sleep(random.choice([1.2,2]))
        stockcode = resultdata_list[ii][0][-6:]
        stock_pledge = np.nan
        try:
            df_pledge = tspro.pledge_stat(ts_code=gen_tscode(stockcode))
            if(not df_pledge.empty):
                stock_pledge = df_pledge["pledge_ratio"].values[0]
        except Exception as e:
            time.sleep(600)
            print(e)
        resultdata_list[ii] = resultdata_list[ii] + [stock_pledge]
    title = title + ["股权质押比例"]
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "百日位置(%)", "总交易日", "获利持仓比例", "压力筹码比例", "支撑筹码比例", "10日标准差", "20日标准差", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅", "平均20日振幅", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
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
    except Exception as e:
        print(e)
    for ii in range(len(resultdata_list)):
        time.sleep(random.choice([1.2,2]))
        stockcode = resultdata_list[ii][0][-6:]
        stock_pledge = np.nan
        try:
            df_pledge = tspro.pledge_stat(ts_code=gen_tscode(stockcode))
            if(not df_pledge.empty):
                stock_pledge = df_pledge["pledge_ratio"].values[0]
        except Exception as e:
            time.sleep(600)
            print(e)
        resultdata_list[ii] = resultdata_list[ii] + [stock_pledge]
    title = title + ["股权质押比例"]
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    def EMA_Analyze(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        EMA6 = 0
        EMA12 = 0
        EMA24 = 0
        for ii in reversed(range(min(100, len(stockdata_list)))):
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
        for price in [item/100 for item in range(round(max(closingprice*0.9, lowerprice)*100), round(closingprice*100))];
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
        stable5counter = 0
        stable10counter = 0
        stable20counter = 0
        for ii in range(2, len(stockdata_list)):
            minprice = min(closingprice_list[:ii])
            maxprice = max(closingprice_list[:ii])
            if((maxprice-minprice)>0.05*maxprice):
                stable5counter = ii-1
                break
        for ii in range(stable5counter+1, len(stockdata_list)):
            minprice = min(closingprice_list[:ii])
            maxprice = max(closingprice_list[:ii])
            if((maxprice-minprice)>0.1*maxprice):
                stable10counter = ii-1
                break
        for ii in range(stable10counter+1, len(stockdata_list)):
            minprice = min(closingprice_list[:ii])
            maxprice = max(closingprice_list[:ii])
            if((maxprice-minprice)>0.2*maxprice):
                stable20counter = ii-1
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
    maxprice = max([float(item[3]) for item in stockdata_list[:100]])
    minprice = min([float(item[3]) for item in stockdata_list[:100]])
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
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "百日位置(%)", "收盘价连续最低天数", "最低价连续最低天数", "百日最多跌幅天数", "百日最大连续跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(drop_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "drop_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续跌幅天数", "日累计总跌幅", "放量倍数", "百日位置(%)", "收盘价连续最低天数", "最低价连续最低天数", "百日最多跌幅天数", "百日最大连续跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(drop_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def drop_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    dropcounter = 0
    for ii in range(len(stockdata_list)-1):
        if(float(stockdata_list[ii][9])<0):
            dropcounter += 1
        else:
            break
    if(dropcounter>0):
        droprange = (float(stockdata_list[0][3])-float(stockdata_list[dropcounter][3]))/float(stockdata_list[dropcounter][3])*100
        closingprice = float(stockdata_list[0][3])
        leastprice = float(stockdata_list[0][5])
        volumnratio = float(stockdata_list[0][10])/float(stockdata_list[1][10])
        maxprice = max([float(item[3]) for item in stockdata_list[:100]])
        minprice = min([float(item[3]) for item in stockdata_list[:100]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        closingcounter = 0
        leastcounter = 0
        for ii in range(1, len(stockdata_list)):
            if(leastprice<float(stockdata_list[ii][3])):
                leastcounter += 1
            else:
                break
        for ii in range(1, len(stockdata_list)):
            if(closingprice<float(stockdata_list[ii][3])):
                closingcounter += 1
            else:
                break
        maxdropcounter = 0
        maxdroprange = 0
        for ii in range(dropcounter, min(100,len(stockdata_list))):
            tempdropcounter = 0
            for jj in range(ii, len(stockdata_list)-1):
                if(float(stockdata_list[jj][9])<0):
                    tempdropcounter += 1
                else:
                    tempdroprange = (float(stockdata_list[ii][3])-float(stockdata_list[ii+tempdropcounter][3]))/float(stockdata_list[ii+tempdropcounter][3])*100
                    if(tempdroprange<maxdroprange):
                        maxdroprange = tempdroprange
                    if(tempdropcounter>maxdropcounter):
                        maxdropcounter = tempdropcounter
                    break
        return [stockinfo, stockdata_list[0][9], dropcounter, droprange, volumnratio, reboundrange, closingcounter, leastcounter, maxdropcounter, maxdroprange]
    else:
        return []


def rise_Model_Select():
# 连续多日上涨(&阳线)模型
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "百日位置(%)", "收盘价连续最高天数", "最高价连续最高天数", "百日最多涨幅天数", "百日最大连续涨幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(rise_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def rise_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "rise_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "连续上涨天数",  "日累计总涨幅", "放量倍数", "百日位置(%)", "收盘价连续最高天数", "最高价连续最高天数", "百日最多涨幅天数", "百日最大连续涨幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(rise_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def rise_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    risecounter = 0
    for ii in range(len(stockdata_list)-1):
#        if((float(stockdata_list[ii][9])>0) or (float(stockdata_list[ii][3])>float(stockdata_list[ii][6]))):
#        if(float(stockdata_list[ii][3])>float(stockdata_list[ii][6])):
        if(float(stockdata_list[ii][9])>0):
            risecounter += 1
        else:
            break
    if(risecounter>0):
        riserange = (float(stockdata_list[0][3])-float(stockdata_list[risecounter][3]))/float(stockdata_list[risecounter][3])*100
        closingprice = float(stockdata_list[0][3])
        topprice = float(stockdata_list[0][4])
        maxprice = max([float(item[3]) for item in stockdata_list[:100]])
        minprice = min([float(item[3]) for item in stockdata_list[:100]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        volumnratio = float(stockdata_list[0][10])/float(stockdata_list[1][10])
        closingcounter = 0
        topcounter = 0
        for ii in range(1, len(stockdata_list)):
            if(topprice>float(stockdata_list[ii][3])):
                topcounter += 1
            else:
                break
        for ii in range(1, len(stockdata_list)):
            if(closingprice>float(stockdata_list[ii][3])):
                closingcounter += 1
            else:
                break
        maxrisecounter = 0
        maxriserange = 0
        for ii in range(risecounter, min(100,len(stockdata_list))):
            temprisecounter = 0
            for jj in range(ii, len(stockdata_list)-1):
                if(float(stockdata_list[jj][9])>0):
                    temprisecounter += 1
                else:
                    tempriserange = (float(stockdata_list[ii][3])-float(stockdata_list[ii+temprisecounter][3]))/float(stockdata_list[ii+temprisecounter][3])*100
                    if(tempriserange>maxriserange):
                        maxriserange = tempriserange
                    if(temprisecounter>maxrisecounter):
                        maxrisecounter = temprisecounter
                    break
        return [stockinfo, stockdata_list[0][9], risecounter, riserange, volumnratio, reboundrange, closingcounter, topcounter, maxrisecounter, maxriserange]
    else:
        return []


def vshape_Model_Select():
# 放量上涨模型
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "相对放量倍数", "前一日跌幅", "后一日涨幅", "前一日开盘价", "前一日收盘价", "前一日最高价", "前一日最低价", "当日开盘价", "当日收盘价", "当日最高价", "当日最低价", "前一日换手率", "后一日换手率"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(vshape_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def vshape_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "vshape_Model_Select_Result.csv")
    title = ["股票名称", "百日位置(%)", "相对放量倍数", "前一日跌幅", "后一日涨幅", "前一日开盘价", "前一日收盘价", "前一日最高价", "前一日最低价", "当日开盘价", "当日收盘价", "当日最高价", "当日最低价", "前一日换手率", "后一日换手率"]
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
        volumn_ratio = (float(stockdata_list[0][10])/float(stockdata_list[1][10]))/abs(float(stockdata_list[0][9])/float(stockdata_list[1][9]))
        return [stockinfo, rebound_range, volumn_ratio, stockdata_list[1][9], stockdata_list[0][9], stockdata_list[1][6], stockdata_list[1][3], stockdata_list[1][4], stockdata_list[1][5], stockdata_list[0][6], stockdata_list[0][3], stockdata_list[0][4], stockdata_list[0][5], stockdata_list[1][10], stockdata_list[0][10]]
    else:
        return []


def shadow_Model_Select():
# 收下影线金针探底模型
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "收盘价", "开盘价", "最高价", "最低价", "百日位置(%)", "换手率量比"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(shadow_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def shadow_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "shadow_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "开盘涨跌幅", "柱线幅度", "下影线幅度", "收盘价", "开盘价", "最高价", "最低价", "百日位置(%)", "换手率量比"]
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
    shadow_range = (min(float(stockdata_list[0][3]), float(stockdata_list[0][6]))-float(stockdata_list[0][5]))/float(stockdata_list[0][7])*100
    cylinder_range = (float(stockdata_list[0][3]) - float(stockdata_list[0][6]))/float(stockdata_list[0][7])*100
    if((float(stockdata_list[0][9])<3) and (shadow_range>3) and (float(stockdata_list[0][5])<min([float(item[3]) for item in stockdata_list[:30]]))):
        return [stockinfo, stockdata_list[0][9], round(open_range,2), round(cylinder_range,2), round(shadow_range,2), stockdata_list[0][3], stockdata_list[0][6], stockdata_list[0][4], stockdata_list[0][5], round(rebound_range,2), round(float(stockdata_list[0][10])/float(stockdata_list[1][10]),2)]
    else:
        return []


def box_Model_Select():
# 箱体模型
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票下跌幅度", "股票反弹幅度", "反弹比例", "股票最高点价格", "股票最低点价格", "股票当前价格", "股票下跌天数", "股票反弹天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(box_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "box_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票下跌幅度", "股票反弹幅度", "反弹比例", "股票最高点价格", "股票最低点价格", "股票当前价格", "股票下跌天数", "股票反弹天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(box_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def box_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    for paratuple in [(400, 0.4), (300, 0.45), (200, 0.5), (100, 0.6), (60, 0.7), (30, 0.8)]:
        closingprice_list = [float(item[3]) for item in stockdata_list[:min(len(stockdata_list), paratuple[0])]]
        maxprice = max(closingprice_list)
        max_offset = closingprice_list.index(maxprice)
        minprice = min(closingprice_list)
        min_offset = closingprice_list.index(minprice)
        if((min_offset>2) and (min_offset<max_offset) and (minprice<paratuple[1]*maxprice)):
            fail_range = (minprice-maxprice)/maxprice*100
            rebound_range = (closingprice-minprice)/maxprice*100
            return [stockinfo, stockdata_list[0][9], fail_range, rebound_range, abs(rebound_range/fail_range), maxprice, minprice, stockdata_list[0][3], (max_offset-min_offset), min_offset]
        else:
            return []


def wave_Model_Select():
# 波浪模型
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近浪底回升", "最近回升天数", "最近浪顶下跌", "最近下跌天数", "上一浪底回升", "上一回升天数", "上一浪顶下跌", "上一下跌天数", "最近浪顶涨跌", "上一浪顶涨跌", "最近浪底涨跌", "上一浪底涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(wave_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近浪底回升", "最近回升天数", "最近浪顶下跌", "最近下跌天数", "上一浪底回升", "上一回升天数", "上一浪顶下跌", "上一下跌天数", "最近浪顶涨跌", "上一浪顶涨跌", "最近浪底涨跌", "上一浪底涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(wave_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    perioddaynum = min(len(stockdata_list), 500)
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
        minprice = minprice_list[upwavecounter]
        maxprice = maxprice_list[upwavecounter+1+downwavecounter]
        sumfailrange = (minprice-maxprice)/maxprice*100
        sumfailcounter = maxoffset_list[upwavecounter+1+downwavecounter] - minoffset_list[upwavecounter]
        sumreboundrange = (closingprice-minprice)/minprice*100
        sumreboundcounter = minoffset_list[upwavecounter]
        failrange = (minprice_list[0]-maxprice_list[0])/maxprice_list[0]*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        reboundrange = (closingprice-minprice_list[0])/minprice_list[0]*100
        reboundcounter = minoffset_list[0]
        lastfailrange = (minprice_list[1]-maxprice_list[1])/maxprice_list[1]*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastreboundrange = (maxprice_list[0]-minprice_list[1])/minprice_list[1]*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        wavepeakratio = (maxprice_list[0]-maxprice_list[1])/maxprice_list[1]*100
        lastwavepeakratio = (maxprice_list[1]-maxprice_list[2])/maxprice_list[2]*100
        wavevallratio = (minprice_list[0]-minprice_list[1])/minprice_list[1]*100
        lastwavevallratio = (minprice_list[1]-minprice_list[2])/minprice_list[2]*100
        maxfailrange = 0
        maxreboundrange = 0
        maxfailcounter = 0
        maxreboundcounter = 0
        for ii in range(2, len(minprice_list)-1):
            tempfailrange = (minprice_list[ii]-maxprice_list[ii])/maxprice_list[ii]*100
            tempreboundrange = (maxprice_list[ii]-minprice_list[ii+1])/minprice_list[ii]*100
            tempfailcounter = maxoffset_list[ii]-minoffset_list[ii]
            tempreboundcounter = minoffset_list[ii+1]-maxoffset_list[ii]
            if(tempfailrange<maxfailrange):
                maxfailrange = tempfailrange
            if(tempreboundrange>maxreboundrange):
                maxreboundrange = tempreboundrange
            if(tempfailcounter>maxfailcounter):
                maxfailcounter = tempfailcounter
            if(tempreboundcounter>maxreboundcounter):
                maxreboundcounter = tempreboundcounter
        return [stockinfo, stockdata_list[0][9], downwavecounter, upwavecounter, reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, wavepeakratio, lastwavepeakratio, wavevallratio, lastwavevallratio, sumreboundrange, sumreboundcounter, sumfailrange, sumfailcounter, maxreboundrange, maxreboundcounter, maxfailrange, maxfailcounter]
    else:
        return []


def volumn_Model_Select():
# 放量模型
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(volumn_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "volumn_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "放量倍数", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(volumn_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def volumn_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    volumn_ratio = float(stockdata_list[0][10])/float(stockdata_list[1][10])
    if(volumn_ratio>2):
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        closingprice = float(stockdata_list[0][3])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        drop5_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        return [stockinfo, stockdata_list[0][9], volumn_ratio, reboundrange, drop5_range, drop10_range, drop30_range]
    else:
        return []


def trend1T5_Model_Select():
# K线图 1日线 贯穿 5日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "1日线上穿5日线预测天数", "5日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "1日线上穿5日线预测天数", "5日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA1_list = []
    MA5_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA1_list.append(float(stockdata_list[ii][3]))
        MA5_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+5]]))
        DIFF_list.append(MA1_list[ii] - MA5_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA5_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = sum([float(item[3]) for item in stockdata_list[:4]])/4
        parallel_price = DIFF_list[0]*5/4+cross_price
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def trend1T10_Model_Select():
# K线图 1日线 贯穿 10日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "1日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T10_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "1日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T10_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA1_list = []
    MA10_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA1_list.append(float(stockdata_list[ii][3]))
        MA10_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+10]]))
        DIFF_list.append(MA1_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA10_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = sum([float(item[3]) for item in stockdata_list[:9]])/9
        parallel_price = DIFF_list[0]*10/9+cross_price
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def trend5T10_Model_Select():
# K线图 5日线 贯穿 10日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "5日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5T10_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "5日线上穿10日线预测天数", "10日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5T10_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA5_list = []
    MA10_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA5_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+5]]))
        MA10_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+10]]))
        DIFF_list.append(MA5_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA10_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = sum([float(item[3]) for item in stockdata_list[:9]])-2*sum([float(item[3]) for item in stockdata_list[:4]])
        parallel_price = 10*DIFF_list[0]+cross_price
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def trend10T30_Model_Select():
# K线图 10日线 贯穿 30日线 	可拓展为 N1日线 贯穿 N2日线
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日线上穿30日线预测天数", "30日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend10T30_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend10T30_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "10日线上穿30日线预测天数", "30日线下方天数", "股票上穿前总跌幅", "当前价格", "日线交叉价格", "日线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend10T30_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend10T30_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    MA10_list = []
    MA30_list = []
    DIFF_list = []
    if(len(stockdata_list)<130):
        return []
    for ii in range(100):
        MA10_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+10]]))
        MA30_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+30]]))
        DIFF_list.append(MA10_list[ii] - MA30_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (float(stockdata_list[0][3])>MA30_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (float(stockdata_list[0][3])-float(stockdata_list[trend_counter][3]))/float(stockdata_list[trend_counter][3])*100
        trend_predict = math.ceil(DIFF_list[0]/(DIFF_list[1]-DIFF_list[0]))
        cross_price = (sum([float(item[3]) for item in stockdata_list[:29]])-3*sum([float(item[3]) for item in stockdata_list[:9]]))/2
        parallel_price = 15*DIFF_list[0]+cross_price
        return [stockinfo, stockdata_list[0][9], trend_predict, trend_counter, trend_range, stockdata_list[0][3], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def KDJ_Model_Select():
# KDJ 模型
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJ_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJ_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    K_list = [50]
    D_list = [50]
    J_list = [50]
    KDJ_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    if(len(stockdata_list)<50):
        return []
    for ii in reversed(range(min(100, len(stockdata_list)-9))):
        C9 = float(stockdata_list[ii][3])
        L9 = min([float(stockdata_list[jj][5]) for jj in range(ii,ii+9)])
        H9 = max([float(stockdata_list[jj][4]) for jj in range(ii,ii+9)])
        if(H9==L9):
            RSV = 50
        else:
            RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[-1]+1/3*RSV
        D = 2/3*D_list[-1]+1/3*K
        J = 3*K-2*D
        K_list.append(K)
        D_list.append(D)
        J_list.append(J)
        KDJ_list.append(K-D)
    if((KDJ_list[-2]<0) and (KDJ_list[-1]>KDJ_list[-2])):
        KDJ_counter = 1
        for ii in reversed(range(len(KDJ_list)-1)):
            if(KDJ_list[ii]<0):
                KDJ_counter += 1
            else:
                break
        KDJ_range = (float(stockdata_list[0][3])-float(stockdata_list[KDJ_counter-1][3]))/float(stockdata_list[KDJ_counter-1][3])*100
        KDJ_predict = math.ceil(KDJ_list[-1]/(KDJ_list[-2]-KDJ_list[-1]))
        K_price = (H9-L9)*K_list[-1]/100+L9
        KDJ_slope = ((K_list[-1]-D_list[-1])-(K_list[-2]-D_list[-2]))/((K_list[-1]+D_list[-1])/2)
        return [stockinfo, stockdata_list[0][9], KDJ_predict, KDJ_counter, KDJ_range, stockdata_list[0][3], round(K_price,2), KDJ_slope, K_list[-1], D_list[-1], J_list[-1], RSV]
    else:
        return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格",  "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFF_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格",  "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFF_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    EMA12 = 0
    EMA26 = 0
    DIFF_list = [0]
    DEA9_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    if(len(stockdata_list)<100):
        return [], []
    for ii in reversed(range(min(200, len(stockdata_list)))):
        EMA12 = 11/13*EMA12 + 2/13*float(stockdata_list[ii][3])
        EMA26 = 25/27*EMA26 + 2/27*float(stockdata_list[ii][3])
        DIFF = EMA12 - EMA26
        DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
        MACD = (DIFF-DEA9)*2
        DIFF_list.append(DIFF)
        DEA9_list.append(DEA9)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA9_list[-2]<0)):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (float(stockdata_list[0][3])-float(stockdata_list[MACD_counter-1][3]))/float(stockdata_list[MACD_counter-1][3])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        slope_price = ((5/8*(MACD_list[-1]*2-MACD_list[-2])+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27))
        parallel_price = (5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(stockdata_list[0][3])
        MACD_result = [stockinfo, stockdata_list[0][9], MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = math.ceil(DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1]))
        cross_price = (25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        slope_price = (2*DIFF_list[-1]-DIFF_list[-2]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        parallel_price = (DIFF_list[-1]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA9_list[-1]/float(stockdata_list[0][3])
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [stockinfo, stockdata_list[0][9], DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def EMV_Model_Select():
# EMV 模型
    resultfile_path1 = os.path.join(resultdata_path, "EMVMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "EMV_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算EMV金叉天数", "EMV下方天数", "上穿前总跌幅", "EMV比例", "EMV斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV比例", "EMV斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        EMVMACD_result, EMV_result = EMV_Model_Select_pipeline(filename)
        resultdata_list1.append(EMVMACD_result)
        resultdata_list2.append(EMV_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def EMV_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "EMVMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "EMV_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算EMV金叉天数", "EMV下方天数", "上穿前总跌幅", "EMV比例", "EMV斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    title2 = ["股票名称", "当日涨跌幅", "估算EMV贯穿天数", "EMV下方天数", "上穿前总跌幅", "EMV比例", "EMV斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EMV_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def EMV_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
    EMVMACD_result = []
    EMV_result = []
    EMV_list = [0]
    MAEMV_list = [0]
    EMVDIFF_list = [0]
    if(len(stockdata_list)<100):
        return [], []
    for ii in reversed(range(min(200, len(stockdata_list)-1))):
        MID = (float(stockdata_list[ii][3])+float(stockdata_list[ii][4])+float(stockdata_list[ii][5]))/3 - (float(stockdata_list[ii-1][3])+float(stockdata_list[ii-1][4])+float(stockdata_list[ii-1][5]))/3
        BRO = float(stockdata_list[ii][10])/max(float(stockdata_list[ii][4])-float(stockdata_list[ii][5]), 0.01)
        EM = MID/BRO
        EMV = EMV_list[-1]*12/14 + EM*2/14
        MAEMV = MAEMV_list[-1]*7/9 + EMV*2/9
        EMVDIFF = EMV-MAEMV
        EMV_list.append(EMV)
        MAEMV_list.append(MAEMV)
        EMVDIFF_list.append(EMVDIFF)
    if((EMV_list[-1]<0) and (EMVDIFF_list[-2]<0) and (EMVDIFF_list[-1]>EMVDIFF_list[-2])):
        EMVDIFF_counter = 1
        for ii in reversed(range(len(EMVDIFF_list)-1)):
            if(EMVDIFF_list[ii]<0):
                EMVDIFF_counter += 1
            else:
                break
        EMV_range = (float(stockdata_list[0][3])-float(stockdata_list[EMVDIFF_counter-1][3]))/float(stockdata_list[EMVDIFF_counter-1][3])*100
        EMV_predict = math.ceil(EMVDIFF_list[-1]/(EMVDIFF_list[-2]-EMVDIFF_list[-1]))
        EMV_ratio = EMV_list[-1]/(float(stockdata_list[0][3])**2)
        EMV_slope = (EMV_list[-1]-EMV_list[-2])/(float(stockdata_list[0][3])**2)
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        drop5_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        EMVMACD_result = [stockinfo, stockdata_list[0][9], EMV_predict, EMVDIFF_counter, EMV_ratio, EMV_range, EMV_slope, reboundrange, drop5_range, drop10_range, drop30_range]
    if((EMV_list[-2]<0) and (EMV_list[-1]>EMV_list[-2])):
        EMV_counter = 1
        for ii in reversed(range(len(EMV_list)-1)):
            if(EMV_list[ii]<0):
                EMV_counter += 1
            else:
                break
        EMV_range = (float(stockdata_list[0][3])-float(stockdata_list[EMV_counter-1][3]))/float(stockdata_list[EMV_counter-1][3])*100
        EMV_predict = math.ceil(EMV_list[-1]/(EMV_list[-2]-EMV_list[-1]))
        EMV_ratio = EMV_list[-1]/(float(stockdata_list[0][3])**2)
        EMV_slope = (EMV_list[-1]-EMV_list[-2])/(float(stockdata_list[0][3])**2)
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        drop5_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        EMV_result = [stockinfo, stockdata_list[0][9], EMV_predict, EMV_counter, EMV_ratio, EMV_range, EMV_slope, reboundrange, drop5_range, drop10_range, drop30_range]        
    return EMVMACD_result, EMV_result


def DMI_Model_Select():
# DMI 模型
    resultfile_path1 = os.path.join(resultdata_path, "DMI_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "ADX_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "EMAPDI", "EMAMDI", "EMADX", "DMI斜率", "百日位置(%)"]
    title2 = ["股票名称", "当日涨跌幅", "EMAPDI", "EMAMDI", "EMADX", "DMI斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
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
    title1 = ["股票名称", "当日涨跌幅", "估算DMI金叉天数", "DMI下方天数", "上穿前总跌幅", "EMAPDI", "EMAMDI", "EMADX", "DMI斜率", "百日位置(%)"]
    title2 = ["股票名称", "当日涨跌幅", "EMAPDI", "EMAMDI", "EMADX", "DMI斜率", "百日位置(%)", "5日总涨跌幅", "10日总涨跌幅", "30日总涨跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(DMI_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def DMI_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    closingprice = float(stockdata_list[0][3])
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
#    EMADX_list = [50]
#    EMAPDI_list = [50]
#    EMAMDI_list = [50]
    if(len(stockdata_list)<100):
        return [], []
    for ii in range(min(200+14, len(stockdata_list)-1)):
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
    for ii in reversed(range(min(200, len(stockdata_list)-15))):
        PDM = sum(PDM_list[ii:ii+14])
        MDM = sum(MDM_list[ii:ii+14])
        TR = sum(TR_list[ii:ii+14])
        PDI = (PDM/TR)*100
        MDI = (MDM/TR)*100
        DMI = PDI - MDI
        DX = abs(PDI-MDI)/(PDI+MDI)*100
        PDI_list.append(PDI)
        MDI_list.append(MDI)
        DMI_list.append(DMI)
        DX_list.append(DX)
        MADX = np.mean(DX_list[-6:])
        MADX_list.append(MADX)
#        EMAPDI = EMAPDI_list[-1]*12/14+PDI*2/14
#        EMAMDI = EMAMDI_list[-1]*12/14+MDI*2/14
#        DMI = EMAPDI - EMAMDI
#        EMADX = EMADX_list[-1]*5/7 + DX*2/7
#        EMAPDI_list.append(EMAPDI)
#        EMAMDI_list.append(EMAMDI)
#        EMADX_list.append(EMADX)
    if((DMI_list[-2]<0) and (DMI_list[-1]>DMI_list[-2])):
        DMI_counter = 1
        for ii in reversed(range(len(DMI_list)-1)):
            if(DMI_list[ii]<0):
                DMI_counter += 1
            else:
                break
        DMI_range = (float(stockdata_list[0][3])-float(stockdata_list[DMI_counter-1][3]))/float(stockdata_list[DMI_counter-1][3])*100
        DMI_predict = math.ceil(DMI_list[-1]/(DMI_list[-2]-DMI_list[-1]))
        DMI_slope = (DMI_list[-1]-DMI_list[-2])
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        DMI_result = [stockinfo, stockdata_list[0][9], DMI_predict, DMI_counter, DMI_range, PDI_list[-1], MDI_list[-1], MADX_list[-1], DMI_slope, reboundrange]
    if((MADX_list[-2]<MADX_list[-3]) and (MADX_list[-2]<MADX_list[-1])):
        DMI_slope = (DMI_list[-1]-DMI_list[-2])
        maxprice = max([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        minprice = min([float(item[3]) for item in stockdata_list[:min(100, len(stockdata_list))]])
        reboundrange = (closingprice-minprice)/(maxprice-minprice)*100
        drop5_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 5)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 5)][3])*100
        drop10_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 10)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 10)][3])*100
        drop30_range = (float(stockdata_list[0][3])-float(stockdata_list[min(len(stockdata_list)-1, 30)][3]))/float(stockdata_list[min(len(stockdata_list)-1, 30)][3])*100
        ADX_result = [stockinfo, stockdata_list[0][9], PDI_list[-1], MDI_list[-1], MADX_list[-1], DMI_slope, reboundrange, drop5_range, drop10_range, drop30_range]
    return DMI_result, ADX_result


def MACDDIFFShort_Model_Select():
# MACD 模型 (6,10,5) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFFShort_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFFShort_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFFShort_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFFShort_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    EMA6 = 0
    EMA10 = 0
    DIFF_list = [0]
    DEA5_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(200, len(stockdata_list)))):
        EMA6 = 5/7*EMA6 + 2/7*float(stockdata_list[ii][3])
        EMA10 = 9/11*EMA10 + 2/11*float(stockdata_list[ii][3])
        DIFF = EMA6 - EMA10
        DEA5 = 4/6*DEA5_list[-1] + 2/6*DIFF
        MACD = (DIFF-DEA5)*2
        DIFF_list.append(DIFF)
        DEA5_list.append(DEA5)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA5_list[-2]<0)):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (float(stockdata_list[0][3])-float(stockdata_list[MACD_counter-1][3]))/float(stockdata_list[MACD_counter-1][3])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA5_list[-1]-5/7*EMA6+9/11*EMA10)/(2/7-2/11)
        slope_price = (3/4*(MACD_list[-1]*2-MACD_list[-2])+DEA5_list[-1]-5/7*EMA6+9/11*EMA10)/(2/7-2/11)
        parallel_price = (3/4*MACD+DEA5_list[-1]-5/7*EMA6+9/11*EMA10)/(2/7-2/11)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA5_list[-1]/float(stockdata_list[0][3])
        MACD_result = [stockinfo, stockdata_list[0][9], MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = math.ceil(DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1]))
        cross_price = (9/11*EMA10-5/7*EMA6)/(2/7-2/11)
        slope_price = (2*DIFF_list[-1]-DIFF_list[-2]+9/11*EMA10-5/7*EMA6)/(2/7-2/11)
        parallel_price = (DIFF_list[-1]+9/11*EMA10-5/7*EMA6)/(2/7-2/11)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA5_list[-1]/float(stockdata_list[0][3])
        DIFF_ratio = DIFF_list[-1]/DEA5_list[-1]
        DIFF_result = [stockinfo, stockdata_list[0][9], DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def MACDDIFFLong_Model_Select():
# MACD 模型 (21,34,8) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(stockdata_path):
        MACD_result, DIFF_result = MACDDIFFLong_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFFLong_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFFLong_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFFLong_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    EMA21 = 0
    EMA34 = 0
    DIFF_list = [0]
    DEA8_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(200, len(stockdata_list)))):
        EMA21 = 20/22*EMA21 + 2/22*float(stockdata_list[ii][3])
        EMA34 = 33/35*EMA34 + 2/35*float(stockdata_list[ii][3])
        DIFF = EMA21 - EMA34
        DEA8 = 7/9*DEA8_list[-1] + 2/9*DIFF
        MACD = (DIFF-DEA8)*2
        DIFF_list.append(DIFF)
        DEA8_list.append(DEA8)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2]) and (DEA8_list[-2]<0)):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (float(stockdata_list[0][3])-float(stockdata_list[MACD_counter-1][3]))/float(stockdata_list[MACD_counter-1][3])*100
        MACD_predict = math.ceil(MACD_list[-1]/(MACD_list[-2]-MACD_list[-1]))
        cross_price = (DEA8_list[-1]-20/22*EMA21+33/35*EMA34)/(2/22-2/35)
        slope_price = (9/14*(MACD_list[-1]*2-MACD_list[-2])+DEA8_list[-1]-20/22*EMA21+33/35*EMA34)/(2/22-2/35)
        parallel_price = (9/14*MACD+DEA8_list[-1]-20/22*EMA21+33/35*EMA34)/(2/22-2/35)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA8_list[-1]/float(stockdata_list[0][3])
        MACD_result = [stockinfo, stockdata_list[0][9], MACD_predict, MACD_counter, DEA_ratio, MACD_range, MACD_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = math.ceil(DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1]))
        cross_price = (33/35*EMA34-20/22*EMA21)/(2/22-2/35)
        slope_price = (2*DIFF_list[-1]-DIFF_list[-2]+33/35*EMA34-20/22*EMA21)/(2/22-2/35)
        parallel_price = (DIFF_list[-1]+33/35*EMA34-20/22*EMA21)/(2/22-2/35)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/float(stockdata_list[0][3])
        DEA_ratio = DEA8_list[-1]/float(stockdata_list[0][3])
        DIFF_ratio = DIFF_list[-1]/DEA8_list[-1]
        DIFF_result = [stockinfo, stockdata_list[0][9], DIFF_predict, DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, stockdata_list[0][3], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def obv_Model_Select():
# OBV模型+多空净额比率法修正+MACD 模型 & DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "obvMACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "obvDIFF_Model_Select_Result.csv")
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
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
    title1 = ["股票名称", "当日涨跌幅", "估算obvMACD贯穿天数", "obvMACD下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    title2 = ["股票名称", "当日涨跌幅", "估算obvDIFF贯穿天数", "obvDIFF下方天数", "上穿前总跌幅", "5日obv", "10日obv", "30日obv"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(obv_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def obv_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    OBVEMA12 = 0
    OBVEMA26 = 0
    OBV_list = [0]
    OBVDIFF_list = [0]
    OBVDEA9_list = [0]
    OBVMACD_list = [0]
    OBVMACD_result = []
    OBVDIFF_result = []
    for ii in reversed(range(min(100, len(stockdata_list)))):
        OBV = float(stockdata_list[ii][10])
        OBVEMA12 = 11/13*OBVEMA12 + 2/13*OBV
        OBVEMA26 = 25/27*OBVEMA26 + 2/27*OBV
        OBVDIFF = OBVEMA12 - OBVEMA26
        OBVDEA9 = 8/10*OBVDEA9_list[-1] + 2/10*OBVDIFF
        OBVMACD = (OBVDIFF-OBVDEA9)*2
        OBV_list.append(OBV)
        OBVDIFF_list.append(OBVDIFF)
        OBVDEA9_list.append(OBVDEA9)
        OBVMACD_list.append((OBVDIFF-OBVDEA9)*2)
    OBVMA5 = sum(OBV_list[-5:])/5
    OBVMA10 = sum(OBV_list[-10:])/10
    OBVMA30 = sum(OBV_list[-30:])/30
    if((OBVMACD_list[-2]<0) and (OBVMACD_list[-1]>OBVMACD_list[-2]) and (OBVDEA9_list[-2]<0)):
        OBVMACD_counter = 1
        for ii in reversed(range(len(OBVMACD_list)-1)):
            if((OBVMACD_list[ii]<0) or (OBVDIFF_list[ii]<0)):
                OBVMACD_counter+=1
            else:
                break
        OBVMACD_range = (float(stockdata_list[0][3])-float(stockdata_list[OBVMACD_counter-1][3]))/float(stockdata_list[OBVMACD_counter-1][3])*100
        OBVMACD_predict = math.ceil(OBVMACD_list[-1]/(OBVMACD_list[-2]-OBVMACD_list[-1]))
        OBVMACD_result = [stockinfo, stockdata_list[0][9], OBVMACD_predict, OBVMACD_counter, OBVMACD_range, OBVMA5, OBVMA10, OBVMA30]
    if((OBVDIFF_list[-2]<0) and (OBVDIFF_list[-1]>OBVDIFF_list[-2])):
        OBVDIFF_counter = 1
        for ii in reversed(range(len(OBVDIFF_list)-1)):
            if(OBVDIFF_list[ii]<0):
                OBVDIFF_counter+=1
            else:
                break
        OBVDIFF_range = (float(stockdata_list[0][3])-float(stockdata_list[OBVDIFF_counter-1][3]))/float(stockdata_list[OBVDIFF_counter-1][3])*100
        OBVDIFF_predict = math.ceil(OBVDIFF_list[-1]/(OBVDIFF_list[-2]-OBVDIFF_list[-1]))
        OBVDIFF_result = [stockinfo, stockdata_list[0][9], OBVDIFF_predict, OBVDIFF_counter, OBVDIFF_range, OBVMA5, OBVMA10, OBVMA30]
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
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(lagging_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def lagging_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "lagging_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
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
    stock_range = (float(comdata_list[0][1])-float(comdata_list[lagging_counter][1]))/float(comdata_list[lagging_counter][1])*100
    com_range = (float(comdata_list[0][3])-float(comdata_list[lagging_counter][3]))/float(comdata_list[lagging_counter][3])*100
    lagging_range = com_range - stock_range
    lagging30_counter, lagging30_range = lagging_calc(comdata_list, 30)
    lagging60_counter, lagging60_range = lagging_calc(comdata_list, 60)
    lagging100_counter, lagging100_range = lagging_calc(comdata_list, 100)
    lagging200_counter, lagging200_range = lagging_calc(comdata_list, 200)
    lagging500_counter, lagging500_range = lagging_calc(comdata_list, 500)
    return [stockinfo, comdata_list[0][2], stock_range, com_range, lagging_range, lagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter]
    

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
    title = ["股票名称", "股票溢价率", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    if(get_AHdata()):
        _, AHCom_list = read_csvfile(AHfile_path)
        for ii in range(len(AHCom_list)):
            stockHinfo = str(AHCom_list[ii][0]) + '_' + str(AHCom_list[ii][5]).zfill(5) + '_' + str(AHCom_list[ii][2]).zfill(7)
            HKfilename = os.path.join(HKdata_path,  stockHinfo+".csv")
            A_Hratio = (1/(1+float(AHCom_list[ii][9]))-1)*100
            for filename in os.listdir(stockdata_path):
                if(str(AHCom_list[ii][2]).zfill(7)==filename.split(".")[0][-7:]):
                    _, HKdata_list = read_csvfile(HKfilename)
                    _, CNdata_list = read_csvfile(os.path.join(stockdata_path, filename))
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
                    resultdata_list.append([stockHinfo, A_Hratio, stock_range, com_range, lagging_range, lagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter])
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
    title = ["股票名称", "股票溢价率", "股票总涨跌幅", "指数总涨跌幅", "股票总滞后幅", "股票滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list = []
    if(get_ABdata()):
        _, ABCom_list = read_csvfile(ABfile_path)
        for ii in range(len(ABCom_list)):
            stockBcode = str(ABCom_list[ii][6]).zfill(7)
            stockBinfo = str(ABCom_list[ii][0]) + '_' + stockBcode + '_' + str(ABCom_list[ii][2]).zfill(7)
            Bfilename = os.path.join(Bdata_path,  stockBinfo+".csv")
            A_Bratio = (1/(1+float(ABCom_list[ii][11]))-1)*100
            for filename in os.listdir(stockdata_path):
                if(str(ABCom_list[ii][2]).zfill(7)==filename.split(".")[0][-7:]):
                    _, Bdata_list = read_csvfile(Bfilename)
                    _, CNdata_list = read_csvfile(os.path.join(stockdata_path, filename))
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
                    resultdata_list.append([stockBinfo, A_Bratio, stock_range, com_range, lagging_range, lagging_counter, lagging30_range, lagging30_counter, lagging60_range, lagging60_counter, lagging100_range, lagging100_counter, lagging200_range, lagging200_counter, lagging500_range, lagging500_counter])
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
                    margin_df=tspro.margin_detail(ts_code=gen_tscode(marginData_list[ii][0][-6:]), start_date=start_time, end_date=end_time)
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
    title = ["股票名称", "上升天数", "下降天数", "峰值", "谷值", "当前融资净余额", "下跌幅度", "反弹幅度", "反弹比例", "峰值股价", "谷值股价", "当前股价", "股价下跌变化", "股价反弹变化", "股价反弹比例"]
    resultdata_list = []
    if(get_margindata()):
        _, marginData_list = read_csvfile(marginfile_path)
        rounddaynum = 10
        for marginData in marginData_list:
            for filename in os.listdir(stockdata_path):
                if(marginData[0][-6:]==filename.split(".")[0][-6:]):
                    _, margin_list = read_csvfile(os.path.join(margindata_path, marginData[0]+'.csv'))
                    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
                    rzjye_list = [(float(margin_list[ii][2])-float(margin_list[ii][3])) for ii in range(len(margin_list))]
                    perioddaynum = min(len(rzjye_list), 500)
                    minoffset = perioddaynum-1
                    maxoffset = perioddaynum-1
                    for ii in range(perioddaynum):
                        if(rzjye_list[ii]==min(rzjye_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])):
                            minoffset = ii
                            break
                    for ii in range(minoffset+1, perioddaynum):
                        if(rzjye_list[ii]==max(rzjye_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)])):
                            maxoffset = ii
                            break
                    minrzjye = rzjye_list[minoffset]
                    maxrzjye = rzjye_list[maxoffset]
                    closingrzjye = rzjye_list[0]
                    rzjyefail_range = (minrzjye-maxrzjye)/maxrzjye*100
                    rzjyerebound_range = (closingrzjye-minrzjye)/maxrzjye*100
                    rzjyerebound_ratio = 0
                    if(rzjyefail_range!=0):
                        rzjyerebound_ratio = abs(rzjyerebound_range/rzjyefail_range)
                    else:
                        rzjyerebound_ratio = 100
                    closingprice = float(stockdata_list[0][3])
                    minprice = float(stockdata_list[minoffset][3])
                    maxprice = float(stockdata_list[maxoffset][3])
                    for ii in range(len(stockdata_list)):
                        if(stockdata_list[ii][0]<=margin_list[minoffset][0]):
                            minprice = float(stockdata_list[ii][3])
#                            minoffset = ii
                            break
                    for ii in range(ii, len(stockdata_list)):
                        if(stockdata_list[ii][0]<=margin_list[maxoffset][0]):
                            maxprice = float(stockdata_list[ii][3])
#                            maxoffset = ii
                            break
                    pricefail_range = (minprice-maxprice)/maxprice*100
                    pricerebound_range = (closingprice-minprice)/maxprice*100
                    pricerebound_ratio = 0
                    if(pricefail_range!=0):
                        pricerebound_ratio = abs(pricerebound_range/pricefail_range)
                    else:
                        pricerebound_ratio = 100
                    resultdata_list.append([marginData[0], minoffset, (maxoffset-minoffset), maxrzjye, minrzjye, rzjye_list[0], rzjyefail_range, rzjyerebound_range, rzjyerebound_ratio, maxprice, minprice, closingprice, pricefail_range, pricerebound_range, pricerebound_ratio])
        write_csvfile(resultfile_path, title, resultdata_list)


def gdzjc_Model_Select():
# 东方财富网增减持数据
    def get_stockzjc():
        with open(stockinfo_file, 'r') as fp:
            for stockinfo in fp.readlines():
                stockinfo = stockinfo.strip()
                stockcode = stockinfo[-6:]
                zjc_title = ["股票名称", "最新价", "涨跌幅(%)", "股东名称", "增减", "方式", "变动开始日", "变动截止日", "公告日", "变动数量(万股)", "占总股本比例(%)", "占流通股比例(%)",  "持股总数(万股)", "占总股本比例", "持流通股数(万股)", "占流通股比例"]
                zjcdata_list = []
                GZiWEAqK = get_jsvar('http://data.eastmoney.com/DataCenter_V3/gdzjc.ashx?pagesize=1000&page=1&js=var%20GZiWEAqK&param=&sortRule=-1&sortType=BDJZ&tabid=all&code={}'.format(stockcode), 'GZiWEAqK')
                if(GZiWEAqK!=None):
                    stockzjc_list = GZiWEAqK['data']
                    if(len(stockzjc_list)!=0):
                        for stockzjc in stockzjc_list:
                            stockzjcitem = stockzjc.split(',')
                            zjcdata_list.append([stockinfo]+stockzjcitem[2:6]+[stockzjcitem[8]]+stockzjcitem[13:16]+[stockzjcitem[6], stockzjcitem[16], stockzjcitem[7]]+stockzjcitem[9:13])
                        write_csvfile(os.path.join(stockgdzjc_path, '{}.csv'.format(stockinfo)), zjc_title, zjcdata_list)
    get_stockzjc()
    resultfile_path = os.path.join(resultdata_path, "gdzjc_Model_Select_Result.csv")
    title = ["股票名称", "最新价", "涨跌幅(%)", "股东名称", "增减", "方式", "变动开始日", "变动截止日", "公告日", "变动数量(万股)", "占总股本比例(%)", "占流通股比例(%)",  "持股总数(万股)", "占总股本比例", "持流通股数(万股)", "占流通股比例"]
    resultdata_list = []
    for filename in os.listdir(stockgdzjc_path):
        _, stockzjcdata_list = read_csvfile(os.path.join(stockgdzjc_path, filename))
        stockinfo = filename.split(".")[0]
        if(len(stockzjcdata_list)>0):
            resultdata_list.append(stockzjcdata_list[0])
    write_csvfile(resultfile_path, title, resultdata_list)


def repurchase_Model_Select():
# 股票回购信息汇总
    resultfile_path = os.path.join(resultdata_path, "repurchase_Model_Select_Result.csv")
    title = ["股票代码", "公告日期", "截止日期", "进度", "过期日期", "回购数量", "回购金额", "回购最高价", "回购最低价"]
    resultdata_list = []
    df_repurchase = tspro.repurchase(ann_date="")
    for item in df_repurchase.values:
        if(item[0][:3]!="300"):
            resultdata_list.append(list(item))
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
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(KDJMonth_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJMonth_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "预测金叉月数", "KDJ下方月数", "上穿前总跌幅", "当前价格", "预测交叉价格", "KDJ斜率", "K值", "D值", "J值", "RSV"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    if(len(monthclosingprice_list)<12):
        return []
    K_list = [50]
    D_list = [50]
    J_list = [50]
    KDJ_list = [0]
    RSV = 0
    C9 = 0
    L9 = 0
    H9 = 0
    for ii in reversed(range(min(100, len(monthclosingprice_list)-9))):
        C9 = monthclosingprice_list[ii]
        H9 = max([monthmaxprice_list[jj] for jj in range(ii,ii+9)])
        L9 = min([monthminprice_list[jj] for jj in range(ii,ii+9)])
        RSV = (C9-L9)/(H9-L9)*100
        K = 2/3*K_list[-1]+1/3*RSV
        D = 2/3*D_list[-1]+1/3*K
        J = 3*K-2*D
        K_list.append(K)
        D_list.append(D)
        J_list.append(J)
        KDJ_list.append(K-D)
    if((KDJ_list[-2]<0) and (KDJ_list[-1]>KDJ_list[-2])):
        KDJ_counter = 1
        for ii in reversed(range(len(KDJ_list)-1)):
            if(KDJ_list[ii]<0):
                KDJ_counter += 1
            else:
                break
        KDJ_range = (monthclosingprice_list[0]-monthclosingprice_list[KDJ_counter-1])/monthclosingprice_list[KDJ_counter-1]*100
        KDJ_predict = KDJ_list[-1]/(KDJ_list[-2]-KDJ_list[-1])
        K_price = (H9-L9)*K_list[-1]/100+L9
        KDJ_slope = ((K_list[-1]-D_list[-1])-(K_list[-2]-D_list[-2]))/((K_list[-1]+D_list[-1])/2)
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, round(KDJ_predict,2), KDJ_counter, KDJ_range, monthclosingprice_list[0], round(K_price,2), KDJ_slope, K_list[-1], D_list[-1], J_list[-1], RSV]
    else:
        return []


def MACDDIFFMonth_Model_Select():
# MACD 模型 (12,26,9)
    resultfile_path1 = os.path.join(resultdata_path, "MACDMonth_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFMonth_Model_Select_Result.csv")
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
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
    title1 = ["股票名称", "当月涨跌幅", "估算MACD贯穿月数", "MACD下方月数", "DEA比例", "上穿前总跌幅", "MACD斜率", "当前价格", "MACD交叉预测价格", "MACD平行预测价格", "MACD不变预测价格"]
    title2 = ["股票名称", "当月涨跌幅", "估算DIFF贯穿月数", "DIFF下方月数", "DIFF/DEA比例", "DEA比例", "DIFF斜率", "当前价格", "DIFF交叉预测价格", "DIFF平行预测价格", "DIFF不变预测价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFFMonth_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFFMonth_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    if(len(monthclosingprice_list)<12):
        return [], []
    EMA12 = 0
    EMA26 = 0
    DIFF_list = [0]
    DEA9_list = [0]
    MACD_list = [0]
    MACD_result = []
    DIFF_result = []
    for ii in reversed(range(min(100, len(monthclosingprice_list)))):
        EMA12 = 11/13*EMA12 + 2/13*monthclosingprice_list[ii]
        EMA26 = 25/27*EMA26 + 2/27*monthclosingprice_list[ii]
        DIFF = EMA12 - EMA26
        DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
        MACD = (DIFF-DEA9)*2
        DIFF_list.append(DIFF)
        DEA9_list.append(DEA9)
        MACD_list.append(MACD)
    if((MACD_list[-2]<0) and (MACD_list[-1]>MACD_list[-2])):
        MACD_counter = 1
        for ii in reversed(range(len(MACD_list)-1)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                MACD_counter+=1
            else:
                break
        MACD_range = (monthclosingprice_list[0]-monthclosingprice_list[MACD_counter-1])/monthclosingprice_list[MACD_counter-1]*100
        MACD_predict = MACD_list[-1]/(MACD_list[-2]-MACD_list[-1])
        cross_price = (DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        slope_price = (5/8*(MACD_list[-1]*2-MACD_list[-2])+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        parallel_price = (5/8*MACD+DEA9_list[-1]-11/13*EMA12+25/27*EMA26)/(2/13-2/27)
        MACD_slope = (MACD_list[-1]-MACD_list[-2])/monthclosingprice_list[0]
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        DEA_ratio = DEA9_list[-1]/monthclosingprice_list[0]
        MACD_result = [stockinfo, month_range, round(MACD_predict,2), MACD_counter, DEA_ratio, MACD_range, MACD_slope, monthclosingprice_list[0], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    if((DIFF_list[-2]<0) and (DIFF_list[-1]>DIFF_list[-2])):
        DIFF_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                DIFF_counter+=1
            else:
                break
        DIFF_predict = DIFF_list[-1]/(DIFF_list[-2]-DIFF_list[-1])
        cross_price = (25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        slope_price = (2*DIFF_list[-1]-DIFF_list[-2]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        parallel_price = (DIFF_list[-1]+25/27*EMA26-11/13*EMA12)/(2/13-2/27)
        DIFF_slope = (DIFF_list[-1]-DIFF_list[-2])/monthclosingprice_list[0]
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        DEA_ratio = DEA9_list[-1]/monthclosingprice_list[0]
        DIFF_ratio = DIFF_list[-1]/DEA9_list[-1]
        DIFF_result = [stockinfo, month_range, round(DIFF_predict,2), DIFF_counter, round(DIFF_ratio,2), DEA_ratio, DIFF_slope, monthclosingprice_list[0], round(cross_price,2), round(slope_price,2), round(parallel_price,2)]
    return MACD_result, DIFF_result


def trend1T5Month_Model_Select():
# K线图 1月线 贯穿 5月线  可拓展为 N1月线 贯穿 N2月线
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "1月线上穿5月线预测月数", "5月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T5Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5Month_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend1T5Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "1月线上穿5月线预测月数", "5月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T5Month_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    MA1_list = []
    MA5_list = []
    DIFF_list = []
    if(len(monthclosingprice_list)<10):
        return []
    for ii in range(min(100, len(monthclosingprice_list)-(5-1))):
        MA1_list.append(monthclosingprice_list[ii])
        MA5_list.append(np.mean(monthclosingprice_list[ii:ii+5]))
        DIFF_list.append(MA1_list[ii] - MA5_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (monthclosingprice_list[0]-monthclosingprice_list[trend_counter])/monthclosingprice_list[trend_counter]*100
        trend_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        cross_price = sum(monthclosingprice_list[:4])/4
        parallel_price = DIFF_list[0]*5/4+cross_price
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, round(trend_predict,2), trend_counter, trend_range, monthclosingprice_list[0], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def trend1T10Month_Model_Select():
# K线图 1月线 贯穿 10月线  可拓展为 N1月线 贯穿 N2月线
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "1月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend1T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T10Month_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend1T10Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "1月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend1T10Month_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    MA1_list = []
    MA10_list = []
    DIFF_list = []
    if(len(monthclosingprice_list)<20):
        return []
    for ii in range(min(100, len(monthclosingprice_list)-(10-1))):
        MA1_list.append(monthclosingprice_list[ii])
        MA10_list.append(np.mean(monthclosingprice_list[ii:ii+10]))
        DIFF_list.append(MA1_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (monthclosingprice_list[0]-monthclosingprice_list[trend_counter])/monthclosingprice_list[trend_counter]*100
        trend_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        cross_price = sum(monthclosingprice_list[:9])/9
        parallel_price = DIFF_list[0]*10/9+cross_price
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, round(trend_predict,2), trend_counter, trend_range, monthclosingprice_list[0], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def trend5T10Month_Model_Select():
# K线图 5月线 贯穿 10月线  可拓展为 N1月线 贯穿 N2月线
    resultfile_path = os.path.join(resultdata_path, "trend5T10Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "5月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    resultdata_list = []
    for filename in os.listdir(stockdata_path):
        resultdata_list.append(trend5T10Month_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5T10Month_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "trend5T10Month_Model_Select_Result.csv")
    title = ["股票名称", "当月涨跌幅", "5月线上穿10月线预测月数", "10月线下方天数", "股票上穿前总跌幅", "当前价格", "月线交叉价格", "月线平行价格"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10Month_Model_Select_pipeline, os.listdir(stockdata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def trend5T10Month_Model_Select_pipeline(filename):
    _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    stockinfo = filename.split(".")[0]
    monthclosingprice_list, monthmaxprice_list, monthminprice_list = get_MonthData(stockdata_list)
    MA5_list = []
    MA10_list = []
    DIFF_list = []
    if(len(monthclosingprice_list)<12):
        return []
    for ii in range(min(100, len(monthclosingprice_list)-(10-1))):
        MA5_list.append(np.mean(monthclosingprice_list[ii:ii+5]))
        MA10_list.append(np.mean(monthclosingprice_list[ii:ii+10]))
        DIFF_list.append(MA5_list[ii] - MA10_list[ii])
    if((DIFF_list[1]<0) and (DIFF_list[0]>DIFF_list[1]) and (monthclosingprice_list[0]>MA10_list[0])):
        trend_counter = 1
        for ii in range(1, len(DIFF_list)):
            if(DIFF_list[ii]<0):
                trend_counter += 1
            else:
                break
        trend_range = (monthclosingprice_list[0]-monthclosingprice_list[trend_counter])/monthclosingprice_list[trend_counter]*100
        trend_predict = DIFF_list[0]/(DIFF_list[1]-DIFF_list[0])
        cross_price = sum(monthclosingprice_list[:9])-2*sum(monthclosingprice_list[:4])
        parallel_price = 10*DIFF_list[0]+cross_price
        month_range = (monthclosingprice_list[0]-monthclosingprice_list[1])/monthclosingprice_list[1]*100
        return [stockinfo, month_range, round(trend_predict,2), trend_counter, trend_range, monthclosingprice_list[0], round(cross_price,2), round(parallel_price,2)]
    else:
        return []


def clear_data():
    if(not os.path.exists(stockdata_path)):
        os.mkdir(stockdata_path)
    for filename in os.listdir(stockdata_path):
        filepath = os.path.join(stockdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
#    if(not os.path.exists(stockgdzjc_path)):
#        os.mkdir(stockgdzjc_path)
#    for filename in os.listdir(stockgdzjc_path):
#        filepath = os.path.join(stockgdzjc_path, filename)
#        if(os.path.exists(filepath)):
#            os.remove(filepath)
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
    summaryfile_list = ["trend1T5_Model_Select_Result.csv", "trend5T10_Model_Select_Result.csv", "trend10T30_Model_Select_Result.csv", "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv",
    "DIFFLong_Model_Select_Result.csv", "MACDLong_Model_Select_Result.csv", "DIFFShort_Model_Select_Result.csv", "MACDShort_Model_Select_Result.csv",
     "KDJ_Model_Select_Result.csv", "DMI_Model_Select_Result.csv", "ADX_Model_Select_Result.csv", "EMV_Model_Select_Result.csv", "EMVMACD_Model_Select_Result.csv",
     "trend1T5Month_Model_Select_Result.csv", "trend5T10Month_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
    for ii in reversed(range(len(summaryfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, summaryfile_list[ii]))):
            summaryfile_list.pop(ii)
    title = ["股票名称", "总和"] + [item.split('_')[0] for item in summaryfile_list]
    stockinfo_list = []
    with open(stockinfo_file, 'r') as fp:
        stockinfo_list = fp.read().splitlines()
    resultdata_list = []
    for stockinfo in stockinfo_list:
        resultdata_list.append(summary_result_pipeline(stockinfo))
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_par():
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
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(summary_result_pipeline, stockinfo_list)
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_pipeline(stockinfo):
    selectfile_list = ["trend1T5_Model_Select_Result.csv", "trend5T10_Model_Select_Result.csv", "trend10T30_Model_Select_Result.csv", "MACD_Model_Select_Result.csv", "DIFF_Model_Select_Result.csv",
    "DIFFLong_Model_Select_Result.csv", "MACDLong_Model_Select_Result.csv", "DIFFShort_Model_Select_Result.csv", "MACDShort_Model_Select_Result.csv",
     "KDJ_Model_Select_Result.csv", "DMI_Model_Select_Result.csv", "ADX_Model_Select_Result.csv", "EMV_Model_Select_Result.csv", "EMVMACD_Model_Select_Result.csv",
     "trend1T5Month_Model_Select_Result.csv", "trend5T10Month_Model_Select_Result.csv", "MACDMonth_Model_Select_Result.csv", "DIFFMonth_Model_Select_Result.csv", "KDJMonth_Model_Select_Result.csv"]
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, selectfile_list[ii]))):
            summaryfile_list.pop(ii)
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
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend1T5_Model_Select Begin!")
#    trend1T5_Model_Select()
    trend1T5_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend1T5_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5T10_Model_Select Begin!")
#    trend5T10_Model_Select()
    trend5T10_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5T10_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend10T30_Model_Select Begin!")
#    trend10T30_Model_Select()
    trend10T30_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend10T30_Model_Select Finished!")
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
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFShort_Model_Select Begin!")
#    MACDDIFFShort_Model_Select()
    MACDDIFFShort_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFShort_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFLong_Model_Select Begin!")
#    MACDDIFFLong_Model_Select()
    MACDDIFFLong_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFFLong_Model_Select Finished!")
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
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend1T5Month_Model_Select Begin!")
#    trend1T5Month_Model_Select()
    trend1T5Month_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend1T5Month_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5T10Month_Model_Select Begin!")
#    trend5T10Month_Model_Select()
    trend5T10Month_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\ttrend5T10Month_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Begin!")
    margin_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tmargin_Model_Select Finished!")
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Begin!")
#    gdzjc_Model_Select()
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tgdzjc_Model_Select Finished!")
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Begin!")
#    similar_Model_Select()
#    similar_Model_Select_par()
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tsimilar_Model_Select Finished!")
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Begin!")
#    repurchase_Model_Select()
#    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\trepurchase_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Begin!")
    AHCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tAHCom_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Begin!")
    ABCom_Model_Select()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tABCom_Model_Select Finished!")


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