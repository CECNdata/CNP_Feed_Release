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
month_range = int(os.getenv("month_range", 3))


# init setup
filter_files=[]
filter_date_part=[]
final_csv=f"{base_dir.split('/')[-1]}_YYYY_MM.csv"
if os.path.exists(mappings_path):
    with open(mappings_path, 'r') as f:
        mappings = json.load(f)

    for key, value in mappings.items():
        final_csv=final_csv.replace(key,value)
    
target_path=os.path.join(target_dir,final_csv)
try:
    os.remove(target_path)
except:pass

# generate date_list for 24 month
def get_last_month(month):
    last_month  = month.replace(day=1)
    last_month -= datetime.timedelta(days=1)
    return(last_month)



# start working
files=os.listdir(base_dir)
files=sorted(files, key=lambda x: x.split(".")[-2], reverse=True) # sort by download time
for file in files:
    try:
        date = re.findall(r"20\d{2}\_\d{1,2}\_\d{1,2}",file)[0] #year_startMonth_endMonth
        part = re.findall(r"part\d*",file)
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
from collections import defaultdict
from dateutil.relativedelta import relativedelta
# 提取发布日期：_YYYY_MM_DD_
def extract_release_date(filename):
    match = re.search(r'_(20\d{2}\_\d{1,2})\_', filename)
    if not match:
        return None
    return datetime.datetime.strptime(match.group(1), "%Y_%m").date()

# 提取更新时间：.YYYYMMDDHHMMSST
def extract_update_time(filename):
    match = re.search(r'\.(\d{14})T', filename)
    if not match:
        return None
    return datetime.datetime.strptime(match.group(1), "%Y%m%d%H%M%S")


# 收集所有文件的 release/update 日期
file_infos = []
for f in filter_files:
    release_date = extract_release_date(f)
    update_time = extract_update_time(f)
    if release_date and update_time:
        file_infos.append((f, release_date, update_time))

# 1. 找到 update_time 最大的文件
latest_file = max(file_infos, key=lambda x: (x[1], x[2]))
latest_release_date=latest_file[1]

# 2. 构造目标 release_date 日期集合（以月为单位）
target_dates = set()
for i in range(month_range):
    d = latest_release_date - relativedelta(months=i)
    target_dates.add(datetime.date(d.year, d.month, d.day))

# 3. 在每个 release_date 中找出 update_time 最大的文件
best_files = {}
for f, r_date, u_time in file_infos:
    if r_date in target_dates:
        if (r_date not in best_files) or (u_time > best_files[r_date][1]):
            best_files[r_date] = (f, u_time)

filter_files = [info[0] for r, info in sorted(best_files.items(), key=lambda x: x[0], reverse=True)]

for f in filter_files:
    # fill zero digit
    df=pd.read_csv(os.path.join(base_dir,f))
    try:
        if '商品编码' in df.columns:
            df['商品编码']=df['商品编码'].apply(lambda x : ('{:0>'+str(fill_zero_bit)+'d}').format(x))
        elif 'Commodity code' in df.columns:
            df['Commodity code']=df['Commodity code'].apply(lambda x : ('{:0>'+str(fill_zero_bit)+'d}').format(x))
    except:pass

    
    # add date column
    date = re.findall(r"20\d{2}_\d{1,2}",f)[0] #year_startMonth_endMonth
    date = date+"_1"
    date = datetime.datetime.strptime(date,"%Y_%m_%d")
    target_path_final=target_path.replace("YYYY_MM",datetime.datetime.strftime(date,"%Y_%m"))
    date = datetime.datetime.strftime(date,"%Y-%m-%d")


    if '商品编码' in df.columns:
        df["时间"]=date
        df_date=df["时间"]
        df_date=df.pop("时间")
        df.insert(0,'时间',df_date)
        if "数据年月" in df.columns:
            df = df.drop(columns=["数据年月"])
            
    last_col = df.columns[-1]
    
    # 去除逗号并转换为数字
    def safe_convert(val):
        try:
            return float(str(val).replace(',', ''))
        except ValueError:
            return val  # 保留原始值

    df[last_col] = df[last_col].apply(safe_convert)

    
    
    # write to 1 csv
    if not os.path.exists(target_path_final):
        df.to_csv(target_path_final, index=False)
    else:
        df.to_csv(target_path_final, mode='a', header=False,  index=False)
