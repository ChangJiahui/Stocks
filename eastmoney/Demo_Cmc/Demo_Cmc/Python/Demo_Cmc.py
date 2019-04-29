
# -*- coding:utf-8 -*-

__author__ = 'Administrator'

from EmQuantAPI import *
import datetime,time
#输入用户名和密码
loginResult = c.start("ForceLogin=1")
#输入板块代码，2000037886为酒、饮料和精制茶制造业行业代码
#输入比较时间段，如最近5天date输入-5
code=c.sector("2000037886",enddate)
date=-5
enddate=str(time.strftime("%Y-%m-%d",time.localtime()))
start_date=c.getdate(enddate,date)
startdate=start_date.Dates[0]
for i in range(len(code.Codes)):
    data=c.cmc(code.Codes[i],"Volume",enddate,enddate,"ishistory=0,ispandas=1")
    hisdata=c.cmc(code.Codes[i],"Volume",startdate,enddate)
    if (hisdata.ErrorCode == 0):
        if ((5*sum(hisdata.Data[0])/len(hisdata.Data[0]))<((data.tail(2)).iat[0,1])):
                    #打印板块代码中最近一分钟交易量是最近5天每分钟平均交易量的5倍以上的代码
                    print code.Codes[i]
                    fl=open('D:/code.txt', 'a')
                    #在D盘code.txt文件中写入符合条件的代码，最近5天每分钟平均交易量和最近一分钟交易量
                    fl.write(str(code.Codes[i])+" :"+str(sum(hisdata.Data[0])/len(hisdata.Data[0]))+"   "+str((data.tail(2)).iat[0,1]))
                    fl.write("\n")
                    fl.close()
        else:
                        pass
    else:
        #历史分钟无数据时输出该注释
        print "History without data"
#程序运行成功
print "end"

