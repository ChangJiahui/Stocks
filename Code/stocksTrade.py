import os
import csv
import tushare as ts
import tunet
import time
import math
import numpy as np


tspro = ts.pro_api("119921ff45f95fd77e5d149cd1e64e78572712b3d0a5ce38157f255b")

end_time = time.strftime('%Y%m%d',time.localtime(time.time()-24*3600))

root_path = "D:\\Workspace\\Python\\Stocks"
stockdata_path = os.path.join(root_path, "Data", "stock_data")
EHBFfile_path = os.path.join(root_path, "Result", "Stocks", "EHBF_Analyze_Result.csv")
accountbook_path = os.path.join(root_path, "Trade.csv")
tradefile_path = os.path.join(root_path, "Trade.log")


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


def clear_data():
    if(os.path.exists(tradefile_path)):
        os.remove(tradefile_path)

    
def trade_analyze():
    def point_Model_Trade_pipeline(tradeitem, stockdata_list):
        maxprice = float(stockdata_list[0][4])
        minprice = float(stockdata_list[0][5])
        if(maxprice>=float(tradeitem[6])*0.95):
            return ("\t接近箱体上沿提示 高位价格: " + str(tradeitem[6]) + "\n")
        elif(minprice<=float(tradeitem[5])*1.05):
            return ("\t接近箱体下沿提示 低位价格: " + str(tradeitem[5]) + "\n")
        else:
            return ""


    def grid_Model_Trade_pipeline(stockLastTradePrice, stockdata_list):
        maxprice = float(stockdata_list[0][4])
        minprice = float(stockdata_list[0][5])
        if(maxprice>=stockLastTradePrice*1.03):
            return ("\t涨3% 网格卖出信号 卖出价格: " + str(round(stockLastTradePrice*1.03,2)) + "\n")
        elif(minprice<=stockLastTradePrice*0.97):
            return ("\t跌3% 网格买入信号 买入价格: " + str(round(stockLastTradePrice*0.97,2)) + "\n")
        else:
            return ""


    def trend1T5_Model_Select_pipeline(stockdata_list):
        N1 = 1
        N2 = 5
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(len(stockdata_list)-N2, 10)
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+N2]]
        MA1_list = []
        MA2_list = []
        DIFF_list = []
        for ii in range(perioddaynum):
            MA1_list.append(np.mean([closingprice_list[ii:ii+N1]]))
            MA2_list.append(np.mean([closingprice_list[ii:ii+N2]]))
            DIFF_list.append(MA1_list[ii] - MA2_list[ii])
        cross_price = (sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        cross_range = (cross_price/closingprice-1)*100
        trend_price = ((2*DIFF_list[0]-DIFF_list[1])+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trend_range = (trend_price/closingprice-1)*100
        parallel_price = (DIFF_list[0]+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallel_range = (parallel_price/closingprice-1)*100
        if((DIFF_list[0]>0) and (DIFF_list[1]<0)):
            return "\t1日线上穿买入信号 买入价格: " + str(round(cross_price,2)) + "\n"
        elif((DIFF_list[0]<0) and (DIFF_list[1]>0)):
            return "\t1日线下穿卖出信号 卖出价格: " + str(round(cross_price,2)) + "\n"
        elif((DIFF_list[0]>DIFF_list[1]) and (DIFF_list[1]<DIFF_list[2])):
            return "\t1日线拐点买入信号 买入价格: " + str(round(parallel_price,2)) + "\n"
        elif((DIFF_list[0]<DIFF_list[1]) and (DIFF_list[1]>DIFF_list[2])):
            return "\t1日线拐点卖出信号 卖出价格: " + str(round(parallel_price,2)) + "\n"
        else:
            return ""
        

    def MACD_Model_Trade_pipeline(stockdata_list):
        N1 = 12
        N2 = 26
        N3 = 9
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(len(stockdata_list)-1, 200)
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
        cross_price = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        cross_range = (cross_price/closingprice-1)*100
        trend_price = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trend_range = (trend_price/closingprice-1)*100
        parallel_price = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallel_range = (parallel_price/closingprice-1)*100
        if((MACD_list[1]<0) and (MACD_list[0]>0)):
            return "\tMACD上穿买入信号 买入价格: " + str(round(cross_price,2)) + "\n"
        elif((MACD_list[1]>0) and (MACD_list[0]<0)):
            return "\tMACD下穿卖出信号 卖出价格: " + str(round(cross_price,2)) + "\n"
        elif((MACD_list[1]<MACD_list[2]) and (MACD_list[1]<MACD_list[0])):
            return "\tMACD拐点买入信号 买入价格: " + str(round(parallel_price,2)) + "\n"
        elif((MACD_list[1]>MACD_list[2]) and (MACD_list[1]>MACD_list[0])):
            return "\tMACD拐点卖出信号 卖出价格: " + str(round(parallel_price,2)) + "\n"
        else:
            return ""


    def KDJ_Model_Trade_pipeline(stockdata_list):
        N = 9
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(len(stockdata_list)-N, 100)
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
        K_price = (H9-L9)*K_list[0]/100+L9
        K_range = (K_price/closingprice-1)*100
        if((DIFF_list[1]<0) and (DIFF_list[0]>0)):
            return "\tKDJ上穿买入信号 买入价格: " + str(round(K_price,2)) + "\n"
        elif((DIFF_list[1]>0) and (DIFF_list[0]<0)):
            return "\tKDJ下穿卖出信号 卖出价格: " + str(round(K_price,2)) + "\n"
        elif((DIFF_list[1]<DIFF_list[2]) and (DIFF_list[1]<DIFF_list[0])):
            return "\tKDJ拐点买入信号 买入价格: " + str(round(K_price,2)) + "\n"
        elif((DIFF_list[1]>DIFF_list[2]) and (DIFF_list[1]>DIFF_list[0])):
            return "\tKDJ拐点卖出信号 卖出价格: " + str(round(K_price,2)) + "\n"
        else:
            return ""


    def DMI_Model_Trade_pipeline(stockdata_list):
        N1 = 14
        N2 = 6
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(len(stockdata_list)-N1-1, 200)
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
        if((DMI_list[1]<0) and (DMI_list[0]>0)):
            return "\tDMI上穿买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((DMI_list[1]>0) and (DMI_list[0]<0)):
            return "\tDMI下穿卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        elif((MADX_list[1]<MADX_list[2]) and (MADX_list[1]<MADX_list[0])):
            return "\tADX拐点反转信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((MADX_list[1]>MADX_list[2]) and (MADX_list[1]>MADX_list[0])):
            return "\tADX拐点反转信号 卖出价格: " + stockdata_list[0][3] + "\n"
        else:
            return ""


    def EMV_Model_Trade_pipeline(stockdata_list):
        N1 = 40
        N2 = 16
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(len(stockdata_list)-1, 300)
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
        if((EMV_list[1]<0) and (EMV_list[0]>0)):
            return "\tEMV上穿买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((EMV_list[1]>0) and (EMV_list[0]<0)):
            return "\tEMV下穿卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        elif((EMVDIFF_list[1]<0) and (EMVDIFF_list[0]>0)):
            return "\tEMV拐点买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((EMVDIFF_list[1]>0) and (EMVDIFF_list[0]<0)):
            return "\tEMV拐点卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        else:
            return ""


    resultstr = ""
    title, trade_list = read_csvfile(accountbook_path)
    for ii in range(len(trade_list)):
        stockinfo = trade_list[ii][0]
        stockLastTradePrice = float(trade_list[ii][3])
        filename = os.path.join(stockdata_path, stockinfo+".csv")
        _, stockdata_list = read_csvfile(filename)
        trade_list[ii][7] = float(trade_list[ii][1])*float(trade_list[ii][2])
        trade_list[ii][8] = float(trade_list[ii][3])*float(trade_list[ii][4])
        trade_list[ii][9] = stockdata_list[0][3]
        trade_list[ii][10] = float(trade_list[ii][5])/float(trade_list[ii][1])-1
        _, EHBFdata_list = read_csvfile(EHBFfile_path)
        for EHBFitem in EHBFdata_list:
                if(EHBFitem[0]==stockinfo):
                    trade_list[ii][11] = EHBFitem[2]
        trade_list[ii][12] = round(stockLastTradePrice*0.97,2)
        trade_list[ii][13] = round(stockLastTradePrice*1.03,2)
        resultstr = resultstr + stockinfo + " 当前价格:" + str(stockdata_list[0][3]) + "\n"
        resultstr = resultstr + point_Model_Trade_pipeline(trade_list[ii], stockdata_list) \
                              + grid_Model_Trade_pipeline(stockLastTradePrice, stockdata_list) \
                              + MACD_Model_Trade_pipeline(stockdata_list) \
                              + KDJ_Model_Trade_pipeline(stockdata_list) \
                              + DMI_Model_Trade_pipeline(stockdata_list) \
                              + EMV_Model_Trade_pipeline(stockdata_list) \
                              + trend1T5_Model_Select_pipeline(stockdata_list)
    write_csvfile(accountbook_path, title, trade_list)
    if(resultstr!=""):
        with open(tradefile_path, 'w') as fp:
            fp.write(resultstr)


def main():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Begin!")
    tunet_connect()
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tNet Connect Finished!")
    if(isMarketOpen()):
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Trade Data Begin!")
        clear_data()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tClear Stock Trade Data Finished!")
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tTrade Analyze Begin!")        
        trade_analyze()
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + ":\tTrade Analyze Finished!")


if __name__=="__main__":
    main()