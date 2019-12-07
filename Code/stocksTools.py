# _file & filename 单个文件路径		_path 文件夹路径
# stockdata_list 1行15列数据  0日期,1股票代码,2名称,3收盘价,4最高价,5最低价,6开盘价,7前收盘,8涨跌额,9涨跌幅,10换手率,11成交量,12成交金额,13总市值,14流通市值


import requests
import random
from bs4 import BeautifulSoup as bs
import time
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
end_time = time.strftime('%Y%m%d',time.localtime(time.time()))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
stockinfo_file = os.path.join(root_path, "Data", "stockinfo.txt")
EHBFfile_path = os.path.join(root_path, "Result", "Stocks", "EHBF_Analyze_Result.csv")
resultdata_path = os.path.join(root_path, "Result", "Tools")
if __name__=="__main__":
    if(not os.path.exists(resultdata_path)):
        os.mkdir(resultdata_path)


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


def holders_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "Holders_Analyze_Select.csv")
    title = ["股票名称",  "股东人数降低季度", "当季股东人数降幅", "股东人数总降幅", "当前股东人数", "百日位置", "盈利比例"]
    resultdata_list = []
    datanum = 0
    with open(stockinfo_file, 'r') as fp:
        for stockinfo in fp.readlines():
            datanum+=1
            time.sleep(random.choice([1,2]))
            stockinfo = stockinfo.strip()
            stockcode = stockinfo[-6:]
            dropcounter = 0
            droprange = 0
            holdernumber = 0
            df_stk_holdernumber = []
            try:
                df_stk_holdernumber = tspro.stk_holdernumber(ts_code=gen_tscode(stockcode), start_date=start_time, end_date=end_time)
            except Exception as e:
                print(e)
                time.sleep(600)
            if(len(df_stk_holdernumber)>5):
                holdernumber = df_stk_holdernumber["holder_num"].values[0]
                for ii in range(len(df_stk_holdernumber)-1):
                    if(df_stk_holdernumber["holder_num"].values[ii]<df_stk_holdernumber["holder_num"].values[ii+1]):
                        dropcounter+=1
                    else:
                        break
                if(dropcounter>0):
                    droprange = (holdernumber-df_stk_holdernumber["holder_num"].values[dropcounter])/df_stk_holdernumber["holder_num"].values[dropcounter]
                    latestdroprange = (holdernumber-df_stk_holdernumber["holder_num"].values[1])/df_stk_holdernumber["holder_num"].values[1]
                    _, EHBFdata_list = read_csvfile(EHBFfile_path)
                    earnratio = "-1"
                    reboundrange = "-1"
                    for EHBFitem in EHBFdata_list:
                        if(EHBFitem[0]==stockinfo):
                            reboundrange = EHBFitem[2]
                            earnratio = EHBFitem[3]
                    resultdata_list.append([stockinfo, dropcounter, latestdroprange, droprange, holdernumber, reboundrange, earnratio])
    write_csvfile(resultfile_path, title, resultdata_list)


if __name__=="__main__":
    tunet_connect()
    holders_Model_Select()