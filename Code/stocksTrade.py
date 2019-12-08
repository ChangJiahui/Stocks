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
    df = tspro.trade_cal(exchange='', start_date=end_time, end_date=end_time)
    df_list = df.values.tolist()
    if(df_list[0][2]==1):
        return True
    else:
        return False


def clear_data():
    if(os.path.exists(tradefile_path)):
        os.remove(tradefile_path)

    
def trade_analyze():
    def grid_Model_Trade_pipeline(stockLastTradePrice, stockdata_list):
        closingPrice = float(stockdata_list[0][3])
        if(closingPrice<stockLastTradePrice*0.95):
            return (" 跌5% 网格买入信号 买入价格: " + str(round(stockLastTradePrice*0.95,2)) + "\n")
        elif(closingPrice>stockLastTradePrice*1.03):
            return (" 涨3% 网格卖出信号 卖出价格: " + str(round(stockLastTradePrice*1.03,2)) + "\n")
        else:
            return ""


    def trend1T5_Model_Select_pipeline(stockdata_list):
        _, stockdata_list = read_csvfile(os.path.join(stockdata_path, filename))
        stockinfo = filename.split(".")[0]
        MA1_list = []
        MA5_list = []
        DIFF_list = []
        for ii in range(10):
            MA1_list.append(float(stockdata_list[ii][3]))
            MA5_list.append(np.mean([float(item[3]) for item in stockdata_list[ii:ii+5]]))
            DIFF_list.append(MA1_list[ii] - MA5_list[ii])
        cross_price = sum([float(item[3]) for item in stockdata_list[:4]])/4
        parallel_price = DIFF_list[-1]*5/4+cross_price
        if((DIFF_list[0]>0) and (DIFF_list[1]<0)):
            return "1日线上穿买入信号 买入价格: " + str(round(cross_price,2)) + "\n"
        elif((DIFF_list[0]<0) and (DIFF_list[1]>0)):
            return "1日线下穿卖出信号 卖出价格: " + str(round(cross_price,2)) + "\n"
        elif((DIFF_list[0]>DIFF_list[1]) and (DIFF_list[1]<DIFF_list[2])):
            return "1日线拐点买入信号 买入价格: " + str(round(parallel_price,2)) + "\n"
        elif((DIFF_list[0]<DIFF_list[1]) and (DIFF_list[1]>DIFF_list[2])):
            return "1日线拐点卖出信号 卖出价格: " + str(round(parallel_price,2)) + "\n"
        else:
            return ""
        


    def MACD_Model_Trade_pipeline(stockdata_list):
        EMA12 = 0
        EMA26 = 0
        DIFF_list = [0]
        DEA9_list = [0]
        MACD_list = [0]
        MACD_result = []
        DIFF_result = []
        for ii in reversed(range(min(200, len(stockdata_list)))):
            EMA12 = 11/13*EMA12 + 2/13*float(stockdata_list[ii][3])
            EMA26 = 25/27*EMA26 + 2/27*float(stockdata_list[ii][3])
            DIFF = EMA12 - EMA26
            DEA9 = 8/10*DEA9_list[-1] + 2/10*DIFF
            MACD = (DIFF-DEA9)*2
            DIFF_list.append(DIFF)
            DEA9_list.append(DEA9)
            MACD_list.append(MACD)
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
        if((MACD_list[-2]<0) and (MACD_list[-1]>0)):
            return " MACD上穿买入信号 买入价格: " + str(round(slope_price,2)) + "\n"
        elif((MACD_list[-2]>0) and (MACD_list[-1]<0)):
            return " MACD下穿卖出信号 卖出价格: " + str(round(slope_price,2)) + "\n"
        elif((MACD_list[-2]<MACD_list[-3]) and (MACD_list[-2]<MACD_list[-1])):
            return " MACD拐点买入信号 买入价格: " + str(round(slope_price,2)) + "\n"
        elif((MACD_list[-2]>MACD_list[-3]) and (MACD_list[-2]>MACD_list[-1])):
            return " MACD拐点卖出信号 卖出价格: " + str(round(slope_price,2)) + "\n"
        else:
            return ""

    def KDJ_Model_Trade_pipeline(stockdata_list):
        K_list = [50]
        D_list = [50]
        J_list = [50]
        KDJ_list = [0]
        RSV = 0
        C9 = 0
        L9 = 0
        H9 = 0
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
        if((KDJ_list[-2]<0) and (KDJ_list[-1]>0)):
            return " KDJ上穿买入信号 买入价格: " + str(round(K_price,2)) + "\n"
        elif((KDJ_list[-2]>0) and (KDJ_list[-1]<0)):
            return " KDJ下穿卖出信号 卖出价格: " + str(round(K_price,2)) + "\n"
        elif((KDJ_list[-2]<KDJ_list[-3]) and (KDJ_list[-2]<KDJ_list[-1])):
            return " KDJ拐点买入信号 买入价格: " + str(round(K_price,2)) + "\n"
        elif((KDJ_list[-2]>KDJ_list[-3]) and (KDJ_list[-2]>KDJ_list[-1])):
            return " KDJ拐点卖出信号 卖出价格: " + str(round(K_price,2)) + "\n"
        else:
            return ""

    def DMI_Model_Trade_pipeline(stockdata_list):
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
#        EMADX_list = [50]
#        EMAPDI_list = [50]
#        EMAMDI_list = [50]
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
#            EMAPDI = EMAPDI_list[-1]*12/14+PDI*2/14
#            EMAMDI = EMAMDI_list[-1]*12/14+MDI*2/14
#            DMI = EMAPDI - EMAMDI
#            EMADX = EMADX_list[-1]*5/7 + DX*2/7
#            EMAPDI_list.append(EMAPDI)
#            EMAMDI_list.append(EMAMDI)
#            EMADX_list.append(EMADX)
        if((DMI_list[-2]<0) and (DMI_list[-1]>0)):
            return " DMI上穿买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((DMI_list[-2]>0) and (DMI_list[-1]<0)):
            return " DMI下穿卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        elif((MADX_list[-2]<MADX_list[-3]) and (MADX_list[-2]<MADX_list[-1])):
            return " ADX拐点买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((MADX_list[-2]>MADX_list[-3]) and (MADX_list[-2]>MADX_list[-1])):
            return " ADX拐点卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        else:
            return ""

    def EMV_Model_Trade_pipeline(stockdata_list):
        EMV_list = [0]
        MAEMV_list = [0]
        DIFF_list = [0]
        for ii in range(min(100, len(stockdata_list)-1)):
            MID = (float(stockdata_list[ii][3])+float(stockdata_list[ii][4])+float(stockdata_list[ii][5]))/3 - (float(stockdata_list[ii-1][3])+float(stockdata_list[ii-1][4])+float(stockdata_list[ii-1][5]))/3
            BRO = float(stockdata_list[ii][10])/max(float(stockdata_list[ii][4])-float(stockdata_list[ii][5]), 0.01)
            EM = MID/BRO
            EMV = EMV_list[-1]*12/14 + EM*2/14
            MAEMV = MAEMV_list[-1]*7/9 + EMV*2/9
            DIFF = EMV-MAEMV
            EMV_list.append(EMV)
            MAEMV_list.append(MAEMV)
            DIFF_list.append(DIFF)
        EMV_counter = 1
        for ii in reversed(range(len(DIFF_list)-1)):
            if(DIFF_list[ii]<0):
                EMV_counter += 1
            else:
                break
        EMV_range = (float(stockdata_list[0][3])-float(stockdata_list[EMV_counter-1][3]))/float(stockdata_list[EMV_counter-1][3])*100
        EMV_predict = math.ceil(EMV_list[-1]/(EMV_list[-2]-EMV_list[-1]))
        if((EMV_list[-2]<0) and (EMV_list[-1]>0)):
            return " EMV上穿买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((EMV_list[-2]>0) and (EMV_list[-1]<0)):
            return " EMV下穿卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        elif((DIFF_list[-2]<0) and (DIFF_list[-1]>0)):
            return " EMV拐点买入信号 买入价格: " + stockdata_list[0][3] + "\n"
        elif((DIFF_list[-2]>0) and (DIFF_list[-1]<0)):
            return " EMV拐点卖出信号 卖出价格: " + stockdata_list[0][3] + "\n"
        else:
            return ""

    resultstr = ""
    title, trade_list = read_csvfile(accountbook_path)
    for ii in range(len(trade_list)):
        stockinfo = trade_list[ii][0]
        stockLastTradePrice = float(trade_list[ii][5])
        filename = os.path.join(stockdata_path, stockinfo+".csv")
        _, stockdata_list = read_csvfile(filename)
        trade_list[ii][1] = stockdata_list[0][3]
        trade_list[ii][4] = float(trade_list[ii][1])*float(trade_list[ii][3])
        trade_list[ii][6] = float(trade_list[ii][1])/float(trade_list[ii][2])-1
        _, EHBFdata_list = read_csvfile(EHBFfile_path)
        for EHBFitem in EHBFdata_list:
                if(EHBFitem[0]==stockinfo):
                    trade_list[ii][7] = EHBFitem[2]
        trade_list[ii][8] = round(stockLastTradePrice*0.95,2)
        trade_list[ii][9] = round(stockLastTradePrice*1.03,2)
        tempstr = grid_Model_Trade_pipeline(stockLastTradePrice, stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
        tempstr = MACD_Model_Trade_pipeline(stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
        tempstr = KDJ_Model_Trade_pipeline(stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
        tempstr = DMI_Model_Trade_pipeline(stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
        tempstr = EMV_Model_Trade_pipeline(stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
        tempstr = trend1T5_Model_Select_pipeline(stockdata_list)
        if(tempstr!=""):
            resultstr = resultstr + stockinfo + tempstr
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