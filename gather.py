#!/usr/bin/env python
# coding=utf-8
import pandas as pd
import os
import re
import datetime
import json

## diy option
fill_zero_bit = int(os.getenv("fill_zero_bit", 2))
base_dir   = os.getenv("base_dir", "./CNP-Customs-total-export-RMB")
target_dir = os.getenv("target_dir", "./")
mappings_path= os.getenv("mappings_path", "./tmp/mappings.json")


# init setup
filter_files=[]
filter_date_part=[]
final_csv=f"{base_dir.split('/')[-1]}.csv"
if os.path.exists(mappings_path):
    with open(mappings_path, 'r') as f:
        mappings = json.load(f)

    for key, value in mappings.items():
        final_csv=final_csv.replace(key,value)
print(final_csv)
    
target_path=os.path.join(target_dir,final_csv)
try:
    os.remove(target_path)
except:pass

# generate date_list for 24 month
def get_last_month(month):
    last_month  = month.replace(day=1)
    last_month -= datetime.timedelta(days=1)
    return(last_month)
today   = datetime.datetime.utcnow()
cn_date = today + datetime.timedelta(hours = 8)



# start working
files=os.listdir(base_dir)
files=sorted(files, key=lambda x: x.split(".")[-2], reverse=True) # sort by download time
for file in files:
    try:
        date = re.findall("20\d{2}_\d{1,2}_\d{1,2}",file)[0] #year_startMonth_endMonth
        part = re.findall("part\d*",file)
        if len(part)==0:
            date_part=str(date)
        else:
            date_part = f"{date}_{part[0]}"
        if date_part not in filter_date_part:
            filter_date_part.append(date_part)
            filter_files.append(file)
    except Exception as e:
        print(e)
        pass

# sort by download time
filter_files = sorted(filter_files, key=lambda x: datetime.datetime.strptime(re.findall("20\d{2}_\d{1,2}_\d{1,2}", x)[0], "%Y_%m_%d"), reverse=True)

for f in filter_files:
    # fill zero digit
    print(f)
    df=pd.read_csv(os.path.join(base_dir,f))
    df['商品编码']=df['商品编码'].apply(lambda x : ('{:0>'+str(fill_zero_bit)+'d}').format(x))

    # add date column
    date = re.findall("20\d{2}_\d{1,2}",f)[0] #year_startMonth_endMonth
    date = date+"_1"
    date = datetime.datetime.strptime(date,"%Y_%m_%d")
    date = datetime.datetime.strftime(date,"%Y-%m-%d")
    df["时间"]=date
    df_date=df["时间"]
    df_date=df.pop("时间")
    df.insert(0,'时间',df_date)
    if "数据年月" in df.columns:
        df = df.drop(columns=["数据年月"])

    # write to 1 csv
    if not os.path.exists(target_path):
        df.to_csv(target_path, index=False)
    else:
        df.to_csv(target_path, mode='a', header=False,  index=False)
