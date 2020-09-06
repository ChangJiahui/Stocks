#coding:utf-8
# _file & filename 单个文件路径       _path 文件夹路径
# bonddata_list 1行11列数据  0可转债代码,1交易日期,2前收盘价,3开盘价,4最高价,5最低价,6收盘价,7涨跌额,8涨跌幅,9成交量,10成交金额


import os
import time
import random
import tunet
import requests
import execjs
from bs4 import BeautifulSoup
import urllib
import re
import multiprocessing
import csv
import math
import numpy as np
import tushare as ts
import statsmodels.api as sm



tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6788.400 QQBrowser/10.3.2888.400'}

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()-24*3600))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
bond_file = os.path.join(root_path, "Data", "bond.csv")
bondinfo_file = os.path.join(root_path, "Data", "bondinfo.txt")
stockdata_path = os.path.join(root_path, "Data", "stock_data")
bonddata_path = os.path.join(root_path, "Data", "bond_data")
resultdata_path = os.path.join(root_path, "Result", "Bonds")
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


def write_csvfile(filename, title, data_list):
    with open(filename, 'w') as fp:
        fp.write(",".join([str(item) for item in title]) + "\n")
        for row_item in data_list:
            if(row_item!=[]):
                fp.write(",".join([str(item) for item in row_item]) + "\n")


def get_TSbonddata(bondTScode, start_time, end_time, bonddata_file):
    title = ['转债代码', '交易日期', '昨收盘价(元)', '开盘价(元)', '最高价(元)', '最低价(元)', '收盘价(元)', '涨跌(元)', '涨跌幅(%)', '成交量(手)', '成交额(万元)']
    time.sleep(random.choice([1,2]))
    for ii in range(3):
        try:
            bond_df = tspro.cb_daily(ts_code=bondTScode, start_date=start_time, end_date=end_time)
            bond_df = bond_df[['ts_code','trade_date','pre_close','open','high','low','close','change','pct_chg','vol','amount']]
            bonddata_list = bond_df.values.tolist()
            write_csvfile(bonddata_file, title, bonddata_list)
            check_bonddata(bonddata_file)
            break
        except Exception as e:
            print(e)
            time.sleep(600)


def get_bondinfo():
# 得到可转债信息
    title = ['转债代码', '转债简称', '正股代码', '正股简称',
             '发行期限（年）', '面值', '发行价格', '发行总额（元）',
             '债券余额（元）', '起息日期', '到期日期',
             '补偿利率（%）', '年付息次数', '上市日期', '摘牌日',
             '转股起始日', '转股截止日', '初始转股价', '最新转股价',
             '到期赎回价格(含税)']
    time.sleep(random.choice([1,2]))
    for jj in range(3):
        try:
            bond_df = tspro.cb_basic(fields="ts_code,bond_short_name,stk_code,stk_short_name,maturity,par,issue_price,issue_size,remain_size,value_date,maturity_date,add_rate,pay_per_year,list_date,delist_date,conv_start_date,conv_end_date,first_conv_price,conv_price,maturity_put_price")
            bond_df = bond_df[bond_df['delist_date'].isnull()]
            bond_df = bond_df[bond_df['conv_end_date']>(end_time[0:4]+'-'+end_time[4:6]+'-'+end_time[6:8])]
            bond_list = bond_df.values.tolist()
            bondinfo_list = [item[1]+'_'+item[0] for item in bond_list]
            write_csvfile(bond_file, title, bond_list)
            with open(bondinfo_file, 'w') as fp:
                for item in bondinfo_list:
                    fp.write(item+"\n")
            break
        except Exception as e:
            print(e)
            time.sleep(600)


def get_bonddata():
# 获取可转债历史数据
    with open(bondinfo_file, 'r') as fp:
        for bondinfo in fp.readlines():
            bondinfo = bondinfo.strip()
            if(bondinfo):
                bondTScode = bondinfo.split('_')[-1]
                bonddata_file = os.path.join(bonddata_path,'{}.csv'.format(bondinfo))
                get_TSbonddata(bondTScode, start_time, end_time, bonddata_file)


def check_bonddata(filename):
    title, bonddata_list = read_csvfile(filename)
    for ii in reversed(range(len(bonddata_list))):
        if((float(bonddata_list[ii][3])==0) or (float(bonddata_list[ii][4])==0) or (float(bonddata_list[ii][5])==0) or
        	float((bonddata_list[ii][9])==0) or (float(bonddata_list[ii][10])==0)):
            bonddata_list.pop(ii)
    if(bonddata_list==[]):
        os.remove(filename)
        return False
    else:
        write_csvfile(filename, title, bonddata_list)
        return True

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


def EHBF_Analyze():
# 横盘天数 & 振幅 & EMA & earnratio & PE & PB
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["可转债名称", "当日收盘价", "当日涨跌幅(%)", "当日成交额(万元)", "历史位置(%)", "百日位置(%)", "总交易日", "10日标准差分位", "20日标准差分位", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅分位", "平均20日振幅分位", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["可转债名称", "当日收盘价", "当日涨跌幅(%)", "当日成交额(万元)", "历史位置(%)", "百日位置(%)", "总交易日", "10日标准差分位", "20日标准差分位", "5%横盘天数", "10%横盘天数", "20%横盘天数", "平均10日振幅分位", "平均20日振幅分位", "6日超跌(-6)", "12日超跌(-10)", "24日超跌(-16)", "30日跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    def EMA_Analyze(bonddata_list):
        closingprice = float(bonddata_list[0][6])
        perioddaynum = min(100, len(bonddata_list))
        closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum]]
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
    
    def stable_Analyze(bonddata_list):
        closingprice = float(bonddata_list[0][6])
        perioddaynum = len(bonddata_list)-1
        closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+1]]
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

    def std_Analyze(bonddata_list):
        N1 = 10
        N2 = 20
        closingprice = float(bonddata_list[0][6])
        perioddaynum = min(1000, len(bonddata_list)-N2)
        if(perioddaynum<300):
            return 0.5, 0.5
        closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N2]]
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

    def amplitude_Analyze(bonddata_list):
        N1 = 10
        N2 = 20
        closingprice = float(bonddata_list[0][6])
        perioddaynum = min(1000, len(bonddata_list)-N2)
        if(perioddaynum<300):
            return 0.5, 0.5
        closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N2]]
        upperprice_list = [float(item[4]) for item in bonddata_list[:perioddaynum+N2]]
        lowerprice_list = [float(item[5]) for item in bonddata_list[:perioddaynum+N2]]
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

    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = len(bonddata_list)
    if(perioddaynum<50):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange1 = (closingprice-minprice)/(maxprice-minprice)*100
    closingprice_list = [float(item[6]) for item in bonddata_list[:100]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange2 = (closingprice-minprice)/(maxprice-minprice)*100
    stable5counter, stable10counter, stable20counter = stable_Analyze(bonddata_list)
    EMA6range, EMA12range, EMA24range = EMA_Analyze(bonddata_list)
    std10, std20 = std_Analyze(bonddata_list)
    amplitude10, amplitude20 = amplitude_Analyze(bonddata_list)
    drop30range = (closingprice/closingprice_list[min(30,perioddaynum-1)]-1)*100
    return [bondinfo, closingprice, bonddata_list[0][8], bonddata_list[0][10], reboundrange1, reboundrange2, len(bonddata_list), std10, std20, stable5counter, stable10counter, stable20counter, amplitude10, amplitude20, EMA6range, EMA12range, EMA24range, drop30range]


def wave_Model_Select():
# 波浪模型
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(wave_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(wave_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_pipeline(filename):
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    rounddaynum = 10
    perioddaynum = min(500, len(bonddata_list)-rounddaynum)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum]]
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
        wavevallratio = (minprice_list[0]/minprice_list[1]-1)*100
        wavepeakratio = (maxprice_list[0]/maxprice_list[1]-1)*100
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastwavepeakratio = (maxprice_list[1]/maxprice_list[2]-1)*100
        lastwavevallratio = (minprice_list[1]/minprice_list[2]-1)*100
        minprice = minprice_list[upwavecounter]
        maxprice = maxprice_list[upwavecounter+1+downwavecounter]
        sumfailrange = (minprice/maxprice-1)*100
        sumfailcounter = maxoffset_list[upwavecounter+1+downwavecounter] - minoffset_list[upwavecounter]
        sumreboundrange = (closingprice/minprice-1)*100
        sumreboundcounter = minoffset_list[upwavecounter]
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
        if((failrange<lastfailrange*2/3) and (failcounter>lastfailcounter) and (reboundrange<abs(failrange)/3) and (3<reboundcounter)):
            return [bondinfo, bonddata_list[0][8], downwavecounter, upwavecounter, reboundrange, reboundcounter, failrange, failcounter, wavevallratio, wavepeakratio,
                    lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, lastwavevallratio, lastwavepeakratio,
                    sumreboundrange, sumreboundcounter, sumfailrange, sumfailcounter, maxreboundrange, maxreboundcounter, maxfailrange, maxfailcounter]
    return []


def RSRS_Model_Select():
# RSRS历史择时模型
    resultfile_path = os.path.join(resultdata_path, "RSRS_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "RSRS因子", "beta分位", "rsquared", "最近多头幅度", "最近多头天数", "最近空头幅度", "最近空头天数", "上一多头幅度", "上一多头天数", "上一空头幅度", "上一空头天数", "上二多头幅度", "上二多头天数", "上二空头幅度", "上二空头天数"]
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(RSRS_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def RSRS_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "RSRS_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "RSRS因子", "beta分位", "rsquared", "最近多头幅度", "最近多头天数", "最近空头幅度", "最近空头天数", "上一多头幅度", "上一多头天数", "上一空头幅度", "上一空头天数", "上二多头幅度", "上二多头天数", "上二空头幅度", "上二空头天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(RSRS_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def RSRS_Model_Select_pipeline(filename):
    N = 16
    rounddaynum = 20
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = min(1000, len(bonddata_list)-N)
    if(perioddaynum<300):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in bonddata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in bonddata_list[:perioddaynum+N]]
    beta_list = [0]*perioddaynum
    betadist_list = [0]*perioddaynum
    rsquared_list = [0]*perioddaynum
    zscore_list = [0]*perioddaynum
    zscoredist_list = [0]*perioddaynum
    offset_list = []
    for ii in range(perioddaynum):
        model = sm.OLS(upperprice_list[ii:ii+N], sm.add_constant(lowerprice_list[ii:ii+N]))
        modelfit = model.fit()
        if(len(modelfit.params)==2):
            beta = modelfit.params[1]
            r2 = modelfit.rsquared
            beta_list[ii] = beta
            rsquared_list[ii] = r2
            zscore_list[ii] = beta*r2
            if(r2>0.9):
                offset_list.append(ii)
    betasort_list = sorted(beta_list)
    for ii in range(perioddaynum):
        betadist_list[ii] = betasort_list.index(beta_list[ii])/perioddaynum
    zscoresort_list = sorted(zscore_list)
    for ii in range(perioddaynum):
        zscoredist_list[ii] = zscoresort_list.index(zscore_list[ii])/perioddaynum
    minprice_list = []
    minbeta_list = []
    minoffset_list = []
    maxprice_list = []
    maxbeta_list = []
    maxoffset_list = []
    startoffset = perioddaynum-1
    for ii in range(len(offset_list)):
        if(beta_list[offset_list[ii]]==min([beta_list[kk] for kk in offset_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)]])):
            minprice_list.append(closingprice_list[ii])
            minbeta_list.append(beta_list[ii])
            minoffset_list.append(ii)
            startoffset = ii
            isDrop=True
            break
        if(beta_list[offset_list[ii]]==max([beta_list[kk] for kk in offset_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)]])):
            return []
    for ii in range(startoffset+1, len(offset_list)):
        tempmaxbeta = max([beta_list[kk] for kk in offset_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)]])
        tempminbeta = min([beta_list[kk] for kk in offset_list[max(0,ii-rounddaynum):min(perioddaynum,ii+rounddaynum+1)]])
        if(isDrop):
            if(beta_list[offset_list[ii]]==tempmaxbeta):
                maxprice_list.append(closingprice_list[offset_list[ii]])
                maxbeta_list.append(beta_list[offset_list[ii]])
                maxoffset_list.append(offset_list[ii])
                isDrop=False
            elif((beta_list[offset_list[ii]]==tempminbeta) and (beta_list[offset_list[ii]]<minbeta_list[-1])):
                minprice_list[-1] = closingprice_list[offset_list[ii]]
                minbeta_list[-1] = beta_list[offset_list[ii]]
                minoffset_list[-1] = offset_list[ii]
        else:
            if(beta_list[offset_list[ii]]==tempminbeta):
                minprice_list.append(closingprice_list[offset_list[ii]])
                minbeta_list.append(beta_list[offset_list[ii]])
                minoffset_list.append(offset_list[ii])
                isDrop=True
            elif((beta_list[offset_list[ii]]==tempmaxbeta) and (beta_list[offset_list[ii]]>maxbeta_list[-1])):
                maxprice_list[-1] = closingprice_list[offset_list[ii]]
                maxbeta_list[-1] = beta_list[offset_list[ii]]
                maxoffset_list[-1] = offset_list[ii]
    if((len(minprice_list)>3) and (len(maxprice_list)>3)):
        reboundcounter = minoffset_list[0]
        reboundrange = (closingprice/minprice_list[0]-1)*100
        failcounter = maxoffset_list[0]-minoffset_list[0]
        failrange = (minprice_list[0]/maxprice_list[0]-1)*100
        lastreboundcounter = minoffset_list[1]-maxoffset_list[0]
        lastreboundrange = (maxprice_list[0]/minprice_list[1]-1)*100
        lastfailcounter = maxoffset_list[1]-minoffset_list[1]
        lastfailrange = (minprice_list[1]/maxprice_list[1]-1)*100
        penultreboundcounter = minoffset_list[2]-maxoffset_list[1]
        penultreboundrange = (maxprice_list[1]/minprice_list[2]-1)*100
        penultfailcounter = maxoffset_list[2]-minoffset_list[2]
        penultfailrange = (minprice_list[2]/maxprice_list[2]-1)*100
        sumrange = reboundrange+failrange+lastreboundrange+lastfailrange+penultreboundrange+penultfailrange
        if((reboundrange<20) and (minbeta_list[0]<minbeta_list[1]) and (reboundcounter>3) and (sumrange<-10)):
            return [bondinfo, bonddata_list[0][8], zscore_list[0], betadist_list[0], rsquared_list[0], reboundrange, reboundcounter, failrange, failcounter, lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, penultreboundrange, penultreboundcounter, penultfailrange, penultfailcounter]
    return []


def trend_Model_Select():
# K线图 N1日线 贯穿 N2日线
    title = ["可转债名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(trend1T5_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(trend1T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(trend5T10_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(trend10T30_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def trend_Model_Select_par():
    title = ["可转债名称", "当日涨跌幅", "1日线上穿预测天数", "5日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T5_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T5_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "1日线上穿预测天数", "10日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend1T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend1T10_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "5日线上穿预测天数", "10日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend5T10_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend5T10_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)

    title = ["可转债名称", "当日涨跌幅", "10日线上穿预测天数", "30日线下方天数", "可转债上穿前总跌幅", "DIFF", "DIFF比例", "日线交叉涨跌幅", "日线趋势涨跌幅", "日线平行涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最大DIFF", "日期", "百日最大DIFF比例", "日期"]
    resultfile_path = os.path.join(resultdata_path, "trend10T30_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(trend10T30_Model_Select_pipeline, os.listdir(bonddata_path))
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
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = min(200, len(bonddata_list)-N2)
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N2]]
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
        minDIFFdate = bonddata_list[DIFF_list[:min(100, perioddaynum)].index(minDIFF)][1]
        minDIFFratio = min(DIFFratio_list[:min(100, perioddaynum)])
        minDIFFratiodate = bonddata_list[DIFFratio_list[:min(100, perioddaynum)].index(minDIFFratio)][1]
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
            return [bondinfo, bonddata_list[0][8], modelpredict, modelcounter, modelrange, DIFF_list[0], DIFFratio_list[0], crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDIFF, minDIFFdate, minDIFFratio, minDIFFratiodate]
    return []


def KDJ_Model_Select():
# KDJ 模型 n=9
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低J值", "日期", "百日最高J值", "日期"]
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(KDJ_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "KDJ_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "预测金叉天数", "KDJ下方天数", "上穿前总跌幅", "KDJ斜率", "预测交叉涨跌幅", "K值", "D值", "J值", "RSV", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低J值", "日期", "百日最高J值", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(KDJ_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def KDJ_Model_Select_pipeline(filename):
    N = 9
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = min(400, len(bonddata_list)-N)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N]]
    upperprice_list = [float(item[4]) for item in bonddata_list[:perioddaynum+N]]
    lowerprice_list = [float(item[5]) for item in bonddata_list[:perioddaynum+N]]
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
        maxJdate = bonddata_list[J_list.index(maxJ)][1]
        minJ = min(J_list[:min(100, perioddaynum)])
        minJdate = bonddata_list[J_list.index(minJ)][1]
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
            return [bondinfo, bonddata_list[0][8], modelpredict, modelcounter, modelrange, modelslope, Krange, K_list[0], D_list[0], J_list[0], RSV, maxmodelcounter, maxmodelrange, minJ, minJdate, maxJ, maxJdate]
    return []


def BOLL_Model_Select():
# BOLL 模型 N1=20 N2=2
    resultfile_path = os.path.join(resultdata_path, "BOLL_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "百日位置", "BOLL极限宽", "BOLL下方天数", "BOLL下方涨跌幅", "上一BOLL下穿上轨天数", "下穿涨跌幅", "上一BOLL上穿下轨天数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    resultdata_list = []
    for filename in os.listdir(bonddata_path):
        resultdata_list.append(BOLL_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLL_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "BOLL_Model_Select_Result.csv")
    title = ["可转债名称", "当日涨跌幅", "百日位置", "BOLL极限宽", "BOLL下方天数", "BOLL下方涨跌幅", "上一BOLL下穿上轨天数", "下穿涨跌幅", "上一BOLL上穿下轨天数", "上穿涨跌幅", "BOLL开口", "BOLL趋势"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(BOLL_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def BOLL_Model_Select_pipeline(filename):
    N1 = 20
    N2 = 2
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = min(200, len(bonddata_list)-N1)
    if(perioddaynum<100):
        return []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+N1]]
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
            return [bondinfo, bonddata_list[0][8], reboundrange, WIDTH_list[0], modelcounter, modelrange, upoffset, uprange, dnoffset, dnrange, widthrange, marange]
    return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    title1 = ["可转债名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["可转债名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(bonddata_path):
        MACD_result, DIFF_result = MACDDIFF1_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)

    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(bonddata_path):
        MACD_result, DIFF_result = MACDDIFF2_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)

    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(bonddata_path):
        MACD_result, DIFF_result = MACDDIFF3_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    title1 = ["可转债名称", "当日涨跌幅", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["可转债名称", "当日涨跌幅", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF1_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])

    resultfile_path1 = os.path.join(resultdata_path, "MACDShort_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFShort_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF2_Model_Select_pipeline, os.listdir(bonddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])

    resultfile_path1 = os.path.join(resultdata_path, "MACDLong_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFFLong_Model_Select_Result.csv")
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF3_Model_Select_pipeline, os.listdir(bonddata_path))
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
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, filename))
    bondinfo = filename[:filename.rfind(".")]
    closingprice = float(bonddata_list[0][6])
    perioddaynum = min(400, len(bonddata_list)-1)
    if(perioddaynum<200):
        return [], []
    closingprice_list = [float(item[6]) for item in bonddata_list[:perioddaynum+1]]
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
        minDEAdate = bonddata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][0]
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = bonddata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][0]
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
            MACD_result = [bondinfo, bonddata_list[0][8], modelpredict, modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
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
        minDEAdate = bonddata_list[DEA_list[:min(100, perioddaynum)].index(minDEA)][1]
        DEAratio = min(DEAratio_list[:modelcounter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = bonddata_list[DEAratio_list[:min(100, perioddaynum)].index(minDEAratio)][1]
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
            DIFF_result = [bondinfo, bonddata_list[0][8], modelpredict, modelcounter, modelrange, modelslope, DEA, DEAratio, crossrange, trendrange, parallelrange, maxmodelcounter, maxmodelrange, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
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


def lagging_calc(comdata_list, perioddaynum):
    perioddaynum = min(perioddaynum, len(comdata_list)-1)
    laggingcounter = 0
    for ii in range(perioddaynum):
        if(float(comdata_list[ii][2])<float(comdata_list[ii][4])):
            laggingcounter += 1
    laggingrange = (float(comdata_list[0][3])-float(comdata_list[perioddaynum][3]))/float(comdata_list[perioddaynum][3])*100 - (float(comdata_list[0][1])-float(comdata_list[perioddaynum][1]))/float(comdata_list[perioddaynum][1])*100
    return laggingcounter, laggingrange


def lagging_Model_Select():
# 与正股 相比滞后或领先幅度
    title, bonddata_list = read_csvfile(bond_file)
    resultfile_path1 = os.path.join(resultdata_path, "bondlagging_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "stocklagging_Model_Select_Result.csv")
    title1 = ["债券名称", "当日涨跌幅", "债券总涨跌幅", "股票总涨跌幅", "债券总滞后幅", "总债券滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    title2 = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "债券总涨跌幅", "股票总滞后幅", "总股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    resultdata_list1 = []
    resultdata_list2 = []
    for bonddata_item in bonddata_list:
        bondlagging_result, stocklagging_result = lagging_Model_Select_pipeline(bonddata_item)
        resultdata_list1.append(bondlagging_result)
        resultdata_list2.append(stocklagging_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def lagging_Model_Select_par():
    title, bonddata_list = read_csvfile(bond_file)
    resultfile_path1 = os.path.join(resultdata_path, "bondlagging_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "stocklagging_Model_Select_Result.csv")
    title1 = ["债券名称", "当日涨跌幅", "债券总涨跌幅", "股票总涨跌幅", "债券总滞后幅", "总债券滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    title2 = ["股票名称", "当日涨跌幅", "股票总涨跌幅", "债券总涨跌幅", "股票总滞后幅", "总股票滞后天数", "百日最大连续滞后幅", "百日最大滞后天数", "30日总滞后幅", "30日滞后天数", "60日总滞后幅", "60日滞后天数", "100日总滞后幅", "100日滞后天数", "200日总滞后幅", "200日滞后天数", "500日总滞后幅", "500日滞后天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(lagging_Model_Select_pipeline, bonddata_list)
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def lagging_Model_Select_pipeline(bonddata_item):
    bondinfo = bonddata_item[1]+'_'+bonddata_item[0]
    _, bonddata_list = read_csvfile(os.path.join(bonddata_path, bondinfo+'.csv'))
    stockinfo = ""
    stockdata_list = []
    stockcode = bonddata_item[2].split('.')[0]
    for filename in os.listdir(stockdata_path):
        if(stockcode==filename[-10:-4]):
            stockinfo = filename.split('.')[0]
            _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
    if((len(bonddata_list)<100) or (len(stockdata_list)<100)):
        return [], []
    bondlagging_result = []
    stocklagging_result = []
    offset1 = 0
    offset2 = 0
    comdata1_list = []
    while(True):
        if(stockdata_list[offset1][0].replace('-','')>bonddata_list[offset2][1]):
            comdata1_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], bonddata_list[offset2][6], 0, float(stockdata_list[offset1][3])/float(bonddata_list[offset2][6])])
            offset1+=1
        elif(stockdata_list[offset1][0].replace('-','')<bonddata_list[offset2][1]):
            comdata1_list.append([bonddata_list[offset2][1], stockdata_list[offset1][3], 0, bonddata_list[offset2][6], bonddata_list[offset2][8], float(stockdata_list[offset1][3])/float(bonddata_list[offset2][6])])
            offset2+=1
        else:
            comdata1_list.append([stockdata_list[offset1][0], stockdata_list[offset1][3], stockdata_list[offset1][9], bonddata_list[offset2][6], bonddata_list[offset2][8], float(stockdata_list[offset1][3])/float(bonddata_list[offset2][6])])
            offset1+=1
            offset2+=1
        if(offset1==min(510,len(stockdata_list))):
            break
        if(offset2==min(510,len(bonddata_list))):
            break
    N1 = 12
    N2 = 26
    N3 = 9
    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para([item[5] for item in comdata1_list], N1, N2, N3)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        laggingcounter = 0
        for ii in range(len(MACD_list)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                laggingcounter += 1
            else:
                break
        stockrange = (float(comdata1_list[0][1])/float(comdata1_list[laggingcounter][1])-1)*100
        bondrange = (float(comdata1_list[0][3])/float(comdata1_list[laggingcounter][3])-1)*100
        laggingrange = bondrange - stockrange
        lagging30counter, lagging30range = lagging_calc(comdata1_list, 30)
        lagging60counter, lagging60range = lagging_calc(comdata1_list, 60)
        lagging100counter, lagging100range = lagging_calc(comdata1_list, 100)
        lagging200counter, lagging200range = lagging_calc(comdata1_list, 200)
        lagging500counter, lagging500range = lagging_calc(comdata1_list, 500)
        maxlaggingcounter = 0
        maxlaggingrange = 0
        for ii in range(laggingcounter, min(100, len(comdata1_list)-1)):
            templaggingcounter = 0
            templaggingrange = 0
            for jj in range(ii, min(200, len(comdata1_list)-1)):
                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                    templaggingcounter += 1
                else:
                    break
                templaggingrange = (float(comdata1_list[ii][3])/float(comdata1_list[ii+templaggingcounter][3])-1)*100-(float(comdata1_list[ii][1])/float(comdata1_list[ii+templaggingcounter][1])-1)*100
                if(maxlaggingrange<templaggingrange):
                    maxlaggingrange=templaggingrange
                if(maxlaggingcounter<templaggingcounter):
                    maxlaggingcounter=templaggingcounter
        if((laggingcounter>maxlaggingcounter/2) and (laggingrange>maxlaggingrange*2/3)):
            stocklagging_result = [stockinfo, comdata1_list[0][2], stockrange, bondrange, laggingrange, laggingcounter, maxlaggingrange, maxlaggingcounter, lagging30range, lagging30counter, lagging60range, lagging60counter, lagging100range, lagging100counter, lagging200range, lagging200counter, lagging500range, lagging500counter]
    comdata2_list = []
    for ii in range(len(comdata1_list)):
        comdata2_list.append([comdata1_list[ii][0], comdata1_list[ii][3], comdata1_list[ii][4], comdata1_list[ii][1], comdata1_list[ii][2], 1/comdata1_list[ii][5]])
    N1 = 12
    N2 = 26
    N3 = 9
    EMA1_list, EMA2_list, DIFF_list, DEA_list, DEAratio_list, MACD_list = get_MACD_para([item[5] for item in comdata2_list], N1, N2, N3)
    if((MACD_list[1]<0) and (MACD_list[0]>MACD_list[1]) and (DEA_list[1]<0)):
        laggingcounter = 0
        for ii in range(len(MACD_list)):
            if((MACD_list[ii]<0) or (DIFF_list[ii]<0)):
                laggingcounter += 1
            else:
                break
        bondrange = (float(comdata2_list[0][1])/float(comdata2_list[laggingcounter][1])-1)*100
        stockrange = (float(comdata2_list[0][3])/float(comdata2_list[laggingcounter][3])-1)*100
        laggingrange = stockrange - bondrange 
        lagging30counter, lagging30range = lagging_calc(comdata2_list, 30)
        lagging60counter, lagging60range = lagging_calc(comdata2_list, 60)
        lagging100counter, lagging100range = lagging_calc(comdata2_list, 100)
        lagging200counter, lagging200range = lagging_calc(comdata2_list, 200)
        lagging500counter, lagging500range = lagging_calc(comdata2_list, 500)
        maxlaggingcounter = 0
        maxlaggingrange = 0
        for ii in range(laggingcounter, min(100, len(comdata2_list)-1)):
            templaggingcounter = 0
            templaggingrange = 0
            for jj in range(ii, min(200, len(comdata2_list)-1)):
                if((MACD_list[jj]<0) or (DIFF_list[jj]<0)):
                    templaggingcounter += 1
                else:
                    break
                templaggingrange = (float(comdata2_list[ii][3])/float(comdata2_list[ii+templaggingcounter][3])-1)*100-(float(comdata2_list[ii][1])/float(comdata2_list[ii+templaggingcounter][1])-1)*100
                if(maxlaggingrange<templaggingrange):
                    maxlaggingrange=templaggingrange
                if(maxlaggingcounter<templaggingcounter):
                    maxlaggingcounter=templaggingcounter
        if((laggingcounter>maxlaggingcounter/2) and (laggingrange>maxlaggingrange*2/3)):
            bondlagging_result = [bondinfo, comdata2_list[0][2], bondrange, stockrange, laggingrange, laggingcounter, maxlaggingrange, maxlaggingcounter, lagging30range, lagging30counter, lagging60range, lagging60counter, lagging100range, lagging100counter, lagging200range, lagging200counter, lagging500range, lagging500counter]
    return bondlagging_result, stocklagging_result
    


def clear_data():
    for filename in os.listdir(bonddata_path):
        filepath = os.path.join(bonddata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    for filename in os.listdir(resultdata_path):
        filepath = os.path.join(resultdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def summary_result():
    selectfile_list = os.listdir(resultdata_path)
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    title = ["可转债名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    bondinfo_list = []
    with open(bondinfo_file, 'r') as fp:
        bondinfo_list = fp.read().splitlines()
    resultdata_list = []
    for bondinfo in bondinfo_list:
        resultdata_list.append(summary_result_pipeline(bondinfo))
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_par():
    selectfile_list = os.listdir(resultdata_path)
    resultfile_path = os.path.join(resultdata_path, "summary_result.csv")
    title = ["可转债名称", "总和"] + [item.split('_')[0] for item in selectfile_list]
    bondinfo_list = []
    with open(bondinfo_file, 'r') as fp:
        bondinfo_list = fp.read().splitlines()
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(summary_result_pipeline, bondinfo_list)
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def summary_result_pipeline(bondinfo):
    selectfile_list = os.listdir(resultdata_path)
    for ii in reversed(range(len(selectfile_list))):
        if(not os.path.exists(os.path.join(resultdata_path, selectfile_list[ii]))):
            selectfile_list.pop(ii)
    summary_list = []
    for ii in range(len(selectfile_list)):
        _, selectdata_list = read_csvfile(os.path.join(resultdata_path, selectfile_list[ii]))
        bondinfo_list = [item[0] for item in selectdata_list]
        if(bondinfo in bondinfo_list):
            summary_list.append(1)
        else:
            summary_list.append(0)
    if(sum(summary_list)>0):
        return [bondinfo, sum(summary_list)] + summary_list
    else:
        return []


def analyze_bonddata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Begin!")
    EHBF_Analyze()
#    EHBF_Analyze_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Begin!")
    wave_Model_Select()
#    wave_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
    MACDDIFF_Model_Select()
#    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Begin!")
    KDJ_Model_Select()
#    KDJ_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tKDJ_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLL_Model_Select Begin!")
    BOLL_Model_Select()
#    BOLL_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBOLL_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tRSRS_Model_Select Begin!")
    RSRS_Model_Select()
#    RSRS_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tRSRS_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tlagging_Model_Select Begin!")
    lagging_Model_Select()
#    lagging_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tlagging_Model_Select Finished!")



def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    if(isMarketOpen()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Bond Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Bond Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Bond Info Begin!")
        get_bondinfo()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Bond Info Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBond Data Download Begin!")
        get_bonddata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tBond Data Download Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
        analyze_bonddata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Begin!")
        summary_result()
#        summary_result_par()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tResult Summary Finished!")


if __name__ =="__main__":
    main()