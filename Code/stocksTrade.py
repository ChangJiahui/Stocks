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
        if(maxprice>=float(tradeitem[6])):
            return ("\t突破箱体上沿提示 高位价格: " + str(tradeitem[6]) + "\n")
        elif(minprice<=float(tradeitem[5])):
            return ("\t突破箱体下沿提示 低位价格: " + str(tradeitem[5]) + "\n")
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
        perioddaynum = min(200, len(stockdata_list)-N2)
        if(perioddaynum<10):
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
        crossprice = (sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        crossrange = (crossprice/closingprice-1)*100
        trendprice = ((2*DIFF_list[0]-DIFF_list[1])+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        trendrange = (trendprice/closingprice-1)*100
        parallelprice = (DIFF_list[0]+sum(closingprice_list[:N2-1])/N2-sum(closingprice_list[:N1-1])/N1)/(1/N1-1/N2)
        parallelrange = (parallelprice/closingprice-1)*100
        if((DIFF_list[0]>0) and (DIFF_list[1]<0)):
            return "\t1日线上穿买入信号 买入价格: " + str(round(crossprice,2)) + "\n"
        elif((DIFF_list[0]<0) and (DIFF_list[1]>0)):
            return "\t1日线下穿卖出信号 卖出价格: " + str(round(crossprice,2)) + "\n"
        elif((DIFF_list[0]>DIFF_list[1]) and (DIFF_list[1]<DIFF_list[2])):
            return "\t1日线拐点买入信号 买入价格: " + str(round(parallelprice,2)) + "\n"
        elif((DIFF_list[0]<DIFF_list[1]) and (DIFF_list[1]>DIFF_list[2])):
            return "\t1日线拐点卖出信号 卖出价格: " + str(round(parallelprice,2)) + "\n"
        else:
            return ""
        

    def MACD_Model_Trade_pipeline(stockdata_list):
        N1 = 12
        N2 = 26
        N3 = 9
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(400, len(stockdata_list)-1)
        if(perioddaynum<10):
            return ""
        closingprice_list = [float(item[3]) for item in stockdata_list[:perioddaynum+1]]
        MACD_result = []
        DIFF_result = []
        EMA1_list = [0]*(perioddaynum+1)
        EMA2_list = [0]*(perioddaynum+1)
        DEA_list = [0]*(perioddaynum+1)
        DIFF_list = [0]*perioddaynum
        DEAratio_list = [0]*perioddaynum
        MACD_list = [0]*perioddaynum
        for ii in reversed(range(perioddaynum)):
            EMA1 = (N1-1)/(N1+1)*EMA1_list[ii+1] + 2/(N1+1)*closingprice_list[ii]
            EMA2= (N2-1)/(N2+1)*EMA2_list[ii+1] + 2/(N2+1)*closingprice_list[ii]
            DIFF = EMA1 - EMA2
            DEA = (N3-1)/(N3+1)*DEA_list[ii+1] + 2/(N3+1)*DIFF
            DEAratio = DEA/closingprice_list[ii]
            MACD = (DIFF-DEA)*2
            EMA1_list[ii] = EMA1
            EMA2_list[ii] = EMA2
            DIFF_list[ii] = DIFF
            DEA_list[ii] = DEA
            DEAratio_list[ii] = DEAratio
            MACD_list[ii] = MACD
        crossprice = (DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        crossrange = (crossprice/closingprice-1)*100
        trendprice = ((2*MACD_list[0]-MACD_list[1])/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        trendrange = (trendprice/closingprice-1)*100
        parallelprice = (MACD_list[0]/2*(N3+1)/(N3-1)+DEA_list[0]+(N2-1)/(N2+1)*EMA2_list[0]-(N1-1)/(N1+1)*EMA1_list[0])/(2/(N1+1)-2/(N2+1))
        parallelrange = (parallelprice/closingprice-1)*100
        if((MACD_list[1]<0) and (MACD_list[0]>0)):
            return "\tMACD上穿买入信号 买入价格: " + str(round(crossprice,2)) + "\n"
        elif((MACD_list[1]>0) and (MACD_list[0]<0)):
            return "\tMACD下穿卖出信号 卖出价格: " + str(round(crossprice,2)) + "\n"
        elif((MACD_list[1]<MACD_list[2]) and (MACD_list[1]<MACD_list[0])):
            return "\tMACD拐点买入信号 买入价格: " + str(round(parallelprice,2)) + "\n"
        elif((MACD_list[1]>MACD_list[2]) and (MACD_list[1]>MACD_list[0])):
            return "\tMACD拐点卖出信号 卖出价格: " + str(round(parallelprice,2)) + "\n"
        else:
            return ""


    def KDJ_Model_Trade_pipeline(stockdata_list):
        N = 9
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(400, len(stockdata_list)-N)
        if(perioddaynum<10):
            return ""
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
        Kprice = (H9-L9)*K_list[0]/100+L9
        Krange = (Kprice/closingprice-1)*100
        if((DIFF_list[1]<0) and (DIFF_list[0]>0)):
            return "\tKDJ上穿买入信号 买入价格: " + str(round(Kprice,2)) + "\n"
        elif((DIFF_list[1]>0) and (DIFF_list[0]<0)):
            return "\tKDJ下穿卖出信号 卖出价格: " + str(round(Kprice,2)) + "\n"
        elif((DIFF_list[1]<DIFF_list[2]) and (DIFF_list[1]<DIFF_list[0])):
            return "\tKDJ拐点买入信号 买入价格: " + str(round(Kprice,2)) + "\n"
        elif((DIFF_list[1]>DIFF_list[2]) and (DIFF_list[1]>DIFF_list[0])):
            return "\tKDJ拐点卖出信号 卖出价格: " + str(round(Kprice,2)) + "\n"
        else:
            return ""


    def DMI_Model_Trade_pipeline(stockdata_list):
        N1 = 14
        N2 = 6
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(400, len(stockdata_list)-N1-1)
        if(perioddaynum<10):
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
        perioddaynum = min(400, len(stockdata_list)-1)
        if(perioddaynum<10):
            return ""
        EMV_result = []
        EMVMACD_result = []
        EMV_list = [0]*(perioddaynum+1)
        MAEMV_list = [0]*(perioddaynum+1)
        EMVDIFF_list = [0]*perioddaynum
        EMVratio_list = [0]*perioddaynum
        for ii in reversed(range(perioddaynum)):
            MID = (float(stockdata_list[ii][3])+float(stockdata_list[ii][4])+float(stockdata_list[ii][5]))/3 - (float(stockdata_list[ii+1][3])+float(stockdata_list[ii+1][4])+float(stockdata_list[ii+1][5]))/3
            BRO = float(stockdata_list[ii][4])-float(stockdata_list[ii][5])
            EM = MID*BRO/float(stockdata_list[ii][10])
            EMV = EMV_list[ii+1]*(N1-1)/(N1+1) + EM*2/(N1+1)
            EMVratio = EMV*float(stockdata_list[ii][10])/(float(stockdata_list[ii][3])**2)
            MAEMV = MAEMV_list[ii+1]*(N2-1)/(N2+1) + EMV*2/(N2+1)
            EMVDIFF = EMV-MAEMV
            EMV_list[ii] = EMV
            EMVratio_list[ii] = EMVratio
            MAEMV_list[ii] = MAEMV
            EMVDIFF_list[ii] = EMVDIFF
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

    def wave_Model_Trade_pipeline(stockdata_list):
        closingprice = float(stockdata_list[0][3])
        perioddaynum = min(500, len(stockdata_list))
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
        if((len(minprice_list)>0) and ((len(maxprice_list)>0))):
            failrange = (minprice_list[0]/maxprice_list[0]-1)*100
            failcounter = maxoffset_list[0]-minoffset_list[0]
            reboundrange = (closingprice/minprice_list[0]-1)*100
            reboundcounter = minoffset_list[0]
            retracerange = (closingprice/max(closingprice_list[:minoffset_list[0]])-1)*100
            if(reboundrange<5):
                return "\twave低点买入信号 买入价格: " + str(round(minprice_list[0],2)) + "\n"
            elif(retracerange>-5):
                return "\twave回撤卖出信号 卖出价格: " + str(round(maxprice_list[0],2)) + "\n"
        return ""

    resultstr = ""
    title, trade_list = read_csvfile(accountbook_path)
    for ii in range(len(trade_list)):
        stockinfo = trade_list[ii][0]
        filename = os.path.join(stockdata_path, stockinfo+".csv")
        _, stockdata_list = read_csvfile(filename)
        if(stockdata_list!=[]):
            trade_list[ii][7] = round(float(trade_list[ii][3])*0.97,2)
            trade_list[ii][8] = round(float(trade_list[ii][3])*1.03,2)
            trade_list[ii][9] = stockdata_list[0][3]
            trade_list[ii][10] = float(trade_list[ii][1])*float(trade_list[ii][2])
            trade_list[ii][11] = float(trade_list[ii][3])*float(trade_list[ii][4])
            trade_list[ii][12] = float(trade_list[ii][9])/float(trade_list[ii][1])-1
            resultstr = resultstr + stockinfo + " 当前价格:" + str(stockdata_list[0][3]) + "\n"
            resultstr = resultstr + wave_Model_Trade_pipeline(stockdata_list) \
                                  + grid_Model_Trade_pipeline(float(trade_list[ii][3]), stockdata_list) \
                                  + MACD_Model_Trade_pipeline(stockdata_list) \
                                  + KDJ_Model_Trade_pipeline(stockdata_list) \
                                  + DMI_Model_Trade_pipeline(stockdata_list) \
                                  + EMV_Model_Trade_pipeline(stockdata_list) \
                                  + trend1T5_Model_Select_pipeline(stockdata_list) \
                                  + point_Model_Trade_pipeline(trade_list[ii], stockdata_list)
        else:
            resultstr = stockinfo + " 股票名称错误!" + '\n' + resultstr
            trade_list[ii][7:13] = [0]*6
            trade_list[ii][7] = round(float(trade_list[ii][3])*0.97,2)
            trade_list[ii][8] = round(float(trade_list[ii][3])*1.03,2)
            trade_list[ii][10] = float(trade_list[ii][1])*float(trade_list[ii][2])
            trade_list[ii][11] = float(trade_list[ii][3])*float(trade_list[ii][4])
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