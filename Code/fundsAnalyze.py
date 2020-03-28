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
import tushare as ts


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6788.400 QQBrowser/10.3.2888.400'}

start_time = "19900101"
end_time = time.strftime('%Y%m%d',time.localtime(time.time()-24*3600))
#end_time = "20190621"

root_path = "D:\\Workspace\\Python\\Stocks"
fundinfo_file = os.path.join(root_path, "Data", "fundinfo.txt")
funddata_path = os.path.join(root_path, "Data", "fund_data")
resultdata_path = os.path.join(root_path, "Result", "Funds")
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


def get_htmltext(url):
    for ii in range(10):
        time.sleep(random.choice([1,2]))
        try:
            response = requests.get(url, headers=headers)
#            response = requests.get(url)
#            print("Get Successfully: " + url)
            if(response.status_code!=200):
                return ""
            try:
                html_text = response.content.decode('utf-8-sig')
            except UnicodeDecodeError as e:
#                print(e)
                html_text = response.content.decode('gbk')
#            except NameError as e:
#                print(e)
#                html_text = ""
            return html_text
        except Exception as e:
            print(e)
    return ""


def get_jsvar(url, varname):
    response = get_htmltext(url)
    if(response.find(varname)!=-1):
        return execjs.compile(response).eval(varname)
    else:
        return None


def get_hexundata(fundinfo):
    title = ['时间', '基金信息', '单位净值', '累计净值', "折算净值", "日涨跌幅"]
    fundcode=fundinfo.split('_')[-1]
    hexundata_url = "http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode={}&startdate={}&enddate={}".format(fundcode, (start_time[0:4]+'-'+start_time[4:6]+'-'+start_time[6:8]), (end_time[0:4]+'-'+end_time[4:6]+'-'+end_time[6:8]))
    fhsp_url = "http://fundf10.eastmoney.com/fhsp_{}.html".format(fundcode)
    hexun_res = get_htmltext(hexundata_url)
    fhsp_res = get_htmltext(fhsp_url)
    if((hexun_res!="") and (fhsp_res!="")):
        funddata_list = []
        hexun_soup = BeautifulSoup(hexun_res, "lxml")
        dataset = hexun_soup.find_all('dataset')[0]
        funddata_file = os.path.join(funddata_path,'{}.csv'.format(fundinfo))
        for item in dataset.find_all('data'):
            enddate = item.find_all('fld_enddate')[0].text
            unitnetvalue = item.find_all('fld_unitnetvalue')[0].text
            netvalue = item.find_all('fld_netvalue')[0].text
            funddata_list.append([enddate, fundinfo, unitnetvalue, netvalue, unitnetvalue, 0])
        fhsp_soup = BeautifulSoup(fhsp_res, 'lxml')
        fh_table = fhsp_soup.find_all('table', attrs={'class':'w782 comm cfxq'})[0]
        divident_list = []
        if(len(fh_table.find_all('td'))>1):
            for fh_tr in fh_table.find_all('tr')[1:]:
                fh_td_list = fh_tr.find_all('td')
                registerdate = fh_td_list[1].text
                dividentdate = fh_td_list[2].text
                divident = float(re.findall(r"每份派现金(\d+\.\d+)元", fh_td_list[3].text)[0])
                divident_list.append([registerdate, dividentdate, divident, "sub"])
        sp_table = fhsp_soup.find_all('table', attrs={'class':'w782 comm fhxq'})[0]
        if(len(sp_table.find_all('td'))>1):
            for sp_tr in sp_table.find_all('tr')[1:]:
                sp_td_list = sp_tr.find_all('td')
                dividentdate = sp_td_list[1].text
                dividenttext = sp_td_list[3].text
                if(dividenttext!="暂未披露"):
                    divident = float(re.findall(r"1:(\d+\.\d+)", dividenttext)[0])
                    divident_list.append([dividentdate, dividentdate, divident, "divided"])
        divident_list.sort(reverse=True, key=lambda item: item[1])
        fundoffset = len(funddata_list)
        for ii in reversed(range(len(divident_list))):
            for jj in reversed(range(1, fundoffset)):
                if(funddata_list[jj-1][0]>=divident_list[ii][1]):
                    fundoffset = jj+1
                    proportion = 1
                    if(divident_list[ii][3]=='sub'):
                        proportion = 1-(float(divident_list[ii][2]))/float(funddata_list[jj][4])
                    else:
                        proportion = 1/float(divident_list[ii][2])
                    for kk in range(jj, len(funddata_list)):
                        funddata_list[kk][4] = float(funddata_list[kk][4]) * proportion
                    break
        for ii in range(len(funddata_list)-1):
            funddata_list[ii][5] = ((float(funddata_list[ii][4])/float(funddata_list[ii+1][4]))-1)*100
        write_csvfile(funddata_file, title, funddata_list)
        check_funddata(funddata_file)


def get_funddata():
    with open(fundinfo_file, 'r') as fp:
        for fundinfo in fp.readlines():
            get_hexundata(fundinfo.strip())


def check_funddata(filename):
    title, funddata_list = read_csvfile(filename)
    for ii in reversed(range(len(funddata_list))):
        if((funddata_list[ii][3]=="") or (funddata_list[ii][3]=="0.0000")):
            funddata_list.pop(ii)
    if(funddata_list==[]):
        os.remove(filename)
    else:
        write_csvfile(filename, title, funddata_list)


def get_fundinfo():
# 得到场内交易fund指数基金
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    fund_list = get_jsvar(url, 'r')
    fundinfo_list = []
    for ii in range(len(fund_list)):
#    ["债券型", "混合型", "货币型", "理财型", "保本型", "债券指数", "固定收益", "定开债券", "混合-FOF", "其他创新", "股票型", "分级杠杆", "ETF-场内", "QDII", "QDII-指数", "股票指数", "联接基金", "QDII-ETF"]
        if((fund_list[ii][3] in ["股票型", "分级杠杆", "ETF-场内", "QDII", "QDII-指数", "股票指数", "联接基金", "QDII-ETF"]) and ("(后端)" not in fund_list[ii][2]) and fund_list[ii][2][-1]!='C'):
            fundinfo_list.append(fund_list[ii][3]+'_'+fund_list[ii][2].replace('/','-')+'_'+fund_list[ii][0])
    with open(fundinfo_file, 'w') as fp:
        fp.write("\n".join(fundinfo_list))
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
    title = ["基金名称", "当日涨跌幅", "历史位置(%)", "百日位置(%)", "总交易日", "30日跌幅"]
    resultdata_list = []
    for filename in os.listdir(funddata_path):
        resultdata_list.append(EHBF_Analyze_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_par():
    resultfile_path = os.path.join(resultdata_path, "EHBF_Analyze_Result.csv")
    title = ["股票名称", "当日涨跌幅", "历史位置(%)", "百日位置(%)", "总交易日", "30日跌幅"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(EHBF_Analyze_pipeline, os.listdir(funddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def EHBF_Analyze_pipeline(filename):
    _, funddata_list = read_csvfile(os.path.join(funddata_path, filename))
    fundinfo = filename[:filename.rfind(".")]
    closingprice = float(funddata_list[0][4])
    perioddaynum = len(funddata_list)
    if(perioddaynum<50):
        return []
    closingprice_list = [float(item[4]) for item in funddata_list[:perioddaynum]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange1 = (closingprice-minprice)/(maxprice-minprice)*100
    closingprice_list = [float(item[4]) for item in funddata_list[:100]]
    maxprice = max(closingprice_list)
    minprice = min(closingprice_list)
    reboundrange2 = (closingprice-minprice)/(maxprice-minprice)*100
    drop30range = (closingprice_list[0]/closingprice_list[min(30,perioddaynum-1)]-1)*100
    return [fundinfo, funddata_list[0][5], reboundrange1, reboundrange2, len(funddata_list), drop30range]


def wave_Model_Select():
# 波浪模型
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    resultdata_list = []
    for filename in os.listdir(funddata_path):
        resultdata_list.append(wave_Model_Select_pipeline(filename))
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_par():
    resultfile_path = os.path.join(resultdata_path, "wave_Model_Select_Result.csv")
    title = ["股票名称", "当日涨跌幅", "降浪波数", "升浪波数", "最近回升幅度", "最近回升天数", "最近下跌幅度", "最近下跌天数", "最近浪底涨跌", "最近浪顶涨跌", "上一回升幅度", "上一回升天数", "上一下跌幅度", "上一下跌天数", "上一浪底涨跌", "上一浪顶涨跌", "总回升幅度", "总回升天数", "总下跌幅度", "总下跌天数", "最大回升幅度", "最大回升天数", "最大下跌幅度", "最大下跌天数"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(wave_Model_Select_pipeline, os.listdir(funddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path, title, resultdata_list)
def wave_Model_Select_pipeline(filename):
    _, funddata_list = read_csvfile(os.path.join(funddata_path, filename))
    fundinfo = filename[:filename.rfind(".")]
    closingprice = float(funddata_list[0][4])
    rounddaynum = 10
    perioddaynum = min(500, len(funddata_list)-rounddaynum)
    if(perioddaynum<200):
        return []
    closingprice_list = [float(item[4]) for item in funddata_list[:perioddaynum]]
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
            return [fundinfo, funddata_list[0][5], downwavecounter, upwavecounter, reboundrange, reboundcounter, failrange, failcounter, wavevallratio, wavepeakratio,
                    lastreboundrange, lastreboundcounter, lastfailrange, lastfailcounter, lastwavevallratio, lastwavepeakratio,
                    sumreboundrange, sumreboundcounter, sumfailrange, sumfailcounter, maxreboundrange, maxreboundcounter, maxfailrange, maxfailcounter]
    return []


def MACDDIFF_Model_Select():
# MACD 模型 (12,26,9) & 中间量 DIFF 模型
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["基金信息", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["基金信息", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    resultdata_list1 = []
    resultdata_list2 = []
    for filename in os.listdir(funddata_path):
        MACD_result, DIFF_result = MACDDIFF1_Model_Select_pipeline(filename)
        resultdata_list1.append(MACD_result)
        resultdata_list2.append(DIFF_result)
    write_csvfile(resultfile_path1, title1, resultdata_list1)
    write_csvfile(resultfile_path2, title2, resultdata_list2)
def MACDDIFF_Model_Select_par():
    resultfile_path1 = os.path.join(resultdata_path, "MACD_Model_Select_Result.csv")
    resultfile_path2 = os.path.join(resultdata_path, "DIFF_Model_Select_Result.csv")
    title1 = ["基金信息", "估算MACD贯穿天数", "MACD下方天数", "上穿前总跌幅", "MACD斜率", "DEA", "相对DEA比例", "MACD交叉预测涨跌幅", "MACD趋势预测涨跌幅", "MACD平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    title2 = ["基金信息", "估算DIFF贯穿天数", "DIFF下方天数", "上穿前总跌幅", "DIFF斜率", "DEA", "相对DEA比例", "DIFF交叉预测涨跌幅", "DIFF趋势预测涨跌幅", "DIFF平行预测涨跌幅", "百日最大下方天数", "百日最大上穿前跌幅", "百日最低DEA比例", "日期", "百日最低相对DEA比例", "日期"]
    pool = multiprocessing.Pool(4)
    resultdata_list = pool.map(MACDDIFF1_Model_Select_pipeline, os.listdir(funddata_path))
    pool.close()
    pool.join()
    write_csvfile(resultfile_path1, title1, [item[0] for item in resultdata_list])
    write_csvfile(resultfile_path2, title2, [item[1] for item in resultdata_list])
def MACDDIFF1_Model_Select_pipeline(filename):
    return MACDDIFF_Model_Select_pipeline(filename, 12, 26, 9)
def MACDDIFF_Model_Select_pipeline(filename, N1, N2, N3):
    _, funddata_list = read_csvfile(os.path.join(funddata_path, filename))
    fundinfo = filename[:filename.rfind(".")]
    closingprice = float(funddata_list[0][4])
    perioddaynum = min(500, len(funddata_list)-1)
    if(perioddaynum<200):
        return [], []
    closingprice_list = [float(item[4]) for item in funddata_list[:perioddaynum+1]]
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
        minDEAdate = funddata_list[DEA_list.index(minDEA)][0]
        DEAratio = min(DEAratio_list[:model_counter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = funddata_list[DEAratio_list.index(minDEAratio)][0]
        maxmodel_counter = 0
        maxmodel_range = 0
        for ii in range(model_counter, min(100, perioddaynum)):
            tempmodel_counter = 0
            tempmodel_range = 0
            for jj in range(ii, perioddaynum):
                if(MACD_list[jj]<0):
                    tempmodel_counter += 1
                else:
                    tempmodel_range = (closingprice_list[ii]/closingprice_list[ii+tempmodel_counter]-1)*100
                    if(maxmodel_counter<tempmodel_counter):
                        maxmodel_counter = tempmodel_counter
                    if(maxmodel_range>tempmodel_range):
                        maxmodel_range = tempmodel_range
                    break
        if(model_range<maxmodel_range*2/3):
            MACD_result = [fundinfo, model_predict, model_counter, model_range, model_slope, DEA, DEAratio, round(cross_range,2), round(trend_range,2), round(parallel_range,2), maxmodel_counter, maxmodel_range, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
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
        minDEAdate = funddata_list[DEA_list.index(minDEA)][0]
        DEAratio = min(DEAratio_list[:model_counter])
        minDEAratio = min(DEAratio_list[:min(100, perioddaynum)])
        minDEAratiodate = funddata_list[DEAratio_list.index(minDEAratio)][0]
        maxmodel_counter = 0
        maxmodel_range = 0
        for ii in range(model_counter, min(100, perioddaynum)):
            tempmodel_counter = 0
            tempmodel_range = 0
            for jj in range(ii, perioddaynum):
                if(DIFF_list[jj]<0):
                    tempmodel_counter += 1
                else:
                    tempmodel_range = (closingprice_list[ii]/closingprice_list[ii+tempmodel_counter]-1)*100
                    if(maxmodel_counter<tempmodel_counter):
                        maxmodel_counter = tempmodel_counter
                    if(maxmodel_range>tempmodel_range):
                        maxmodel_range = tempmodel_range
                    break
        if(model_range<maxmodel_range*2/3):
            DIFF_result = [fundinfo, model_predict, model_counter, model_range, model_slope, DEA, DEAratio, round(cross_range,2), round(trend_range,2), round(parallel_range,2), maxmodel_counter, maxmodel_range, minDEA, minDEAdate, minDEAratio, minDEAratiodate]
    return MACD_result, DIFF_result


def clear_data():
    for filename in os.listdir(funddata_path):
        filepath = os.path.join(funddata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)
    for filename in os.listdir(resultdata_path):
        filepath = os.path.join(resultdata_path, filename)
        if(os.path.exists(filepath)):
            os.remove(filepath)


def analyze_funddata():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Begin!")
#    EHBF_Analyze()
    EHBF_Analyze_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tEHBF_Analyze Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Begin!")
#    wave_Model_Select()
    wave_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\twave_Model_Select Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Begin!")
#    MACDDIFF_Model_Select()
    MACDDIFF_Model_Select_par()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tMACDDIFF_Model_Select Finished!")


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Begin!")
    if(isMarketOpen()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Fund Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Fund Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Fund Info Begin!")
        get_fundinfo()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tGenerage Fund Info Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tFund Data Download Begin!")
        get_funddata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tFund Data Download Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Prepare Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Begin!")
        analyze_funddata()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tData Analyze Finished!")


if __name__ =="__main__":
    main()