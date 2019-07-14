def get_stockinfo():
#    url = "http://quote.eastmoney.com/stocklist.html"
    url = "http://quote.eastmoney.com/stock_list.html"
    response = get_htmltext(url)
    if(response==""):
        return False
    else:
        soup = bs(response, 'lxml')
        all_ul = soup.find('div', id='quotesearch').find_all('ul')   # 获取两个ul 标签数据
#        print("开始生成股票列表……")
        with open(stockinfo_file, 'w') as fp:
            for ul in all_ul:
                ull_a = ul.find_all('a')
                for a in ull_a:
                    stock_info = a.text
                    stock_name = stock_info[:stock_info.index('(')]
                    stock_code = stock_info[(stock_info.index('(')+1):stock_info.index(')')]
                    if(("ST" in stock_name) or ("B" in stock_name) or (int(stock_code[0]) not in [0, 2, 6, 9]) or (int(stock_code[:3]) in [201, 202, 203, 204])):
                        continue
                    if(int(stock_code[0]) in [0, 2]):
                        stock_code_new = '1' + stock_code
                    else:
                        stock_code_new = '0' + stock_code
                    if(detect_163data('http://quotes.money.163.com/trade/lsjysj_{}.html'.format(stock_code))):
                        fp.write(stock_name+"_"+stock_code_new+"\n")
#                print("完成股票列表更新……")


def margin_Model_Select():
    resultfile_path = os.path.join(resultdata_path, "margin_Model_Select_Result.csv")
    title = ["股票代码", "股票当日涨跌幅", "融资买入比", "融资净买入比", "融券卖出比", "融券净卖出比"]
    resultdata_list = []
    df = tspro.margin_detail(trade_date=end_time)
    for indexs in df.index:
        time.sleep(random.choice([1,2]))
        margin_item = df.loc[indexs]
        stock_tscode = margin_item['ts_code']
        print(stock_tscode)
        if(float(margin_item['rzye'])==0):
            rzmrb = 0
            rzjmrb = 0
        else:
            rzmrb = float(margin_item['rzmre'])/float(margin_item['rzye'])
            rzjmrb = (float(margin_item['rzmre'])-float(margin_item['rzche']))/float(margin_item['rzye'])
        if(float(margin_item['rqyl'])==0):
            rqmcb = 0
            rqjmcb = 0
        else:
            rqmcb = float(margin_item['rqmcl'])/float(margin_item['rqyl'])
            rqjmcb = (float(margin_item['rqmcl'])-float(margin_item['rqchl']))/float(margin_item['rqyl'])
        df_daily = tspro.daily(ts_code=stock_tscode, trade_date=end_time)
        if(len(df_daily)>0):
            pct_chg = df_daily["pct_chg"].values[0]
        else:
            pct_chg = 0
        resultdata_list.append([stock_tscode, pct_chg, rzmrb, rzjmrb, rqmcb, rqjmcb])
    write_csvfile(resultfile_path, title, resultdata_list)