
"""
Created on Mon Aug  2 15:13:50 2021

@author: Ahmed
"""
#!/usr/bin/env python3
import concurrent.futures
import os 
import os.path
from pydub import AudioSegment
import scipy.signal as signal
import pandas as pd 
import numpy as np
import sys
import time as TIME
import smtplib
import pyodbc
from email.message import EmailMessage
from datetime import datetime
from multiprocessing import freeze_support, Process,Manager
import sklearn.preprocessing as normal

file_mp3 = 1

def read(f, normalized=True):
    """MP3 to numpy array"""
    a = AudioSegment.from_file(f)
    a= a.set_channels(1).set_frame_rate(22050)
    
    y = np.array(a.get_array_of_samples())
    print(a.channels)
    if normalized:
        return a.frame_rate, normal.minmax_scale(y,feature_range = (-1,1),copy = False)#np.float32(y) / 2**15
    else:
        return a.frame_rate, y

def send_email():
    msg = EmailMessage()
    msg.set_content('This is a test message from python script')

    fromEmail = 'XXXXXXXXXXXXXXX'
    toEmail = 'inyathy@outlook.com'

    msg['Subject'] = 'Simple Text Message'
    msg['From'] = fromEmail
    msg['To'] = toEmail

    s = smtplib.SMTP('themediatree.co.za', 587)

    s.starttls()

    s.login(fromEmail, 'XXXXXXX')
    s.send_message(msg)
    print("email sent successfuly..")
    s.quit()   


def date_time():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Yt%H:%M:%S")
    print(dt_string)
    return dt_string.split("t")


def save_audio():
    #now = datetime.now()
    #dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    #
        try:   
            conn = pyodbc.connect('Driver={SQL Server};'
                                'Server=CLAUDEDEV2\SQLEXPRESS;'
                                'Database=TheMediaTree;'
                                'Trusted_Connection=yes;')

            cursor = conn.cursor()
                                
            cursor.execute('''INSERT INTO TheMediaTree.dbo.AudioFiles (FileName)VALUES (?)''', file_mp3) 
            conn.commit()
            conn.close() 
        except:
            pass

def secs_to_time(secs):
    hours = secs/3600.0
    hours_f = hours - int(hours)
    minutes = hours_f * 60.0    
    minutes_f = minutes - int(minutes)
    seconds = minutes_f * 60
    return (int(hours),int(minutes),int(seconds))


def load_audios(names,sample_directory):
    data_frame_samples ={}
    data_frame_samples[names]={'data':0,'sampling_rate':0}
    sample_rate,data = read(sample_directory+"\wav_out\\"+names+".mp3")
    data_frame_samples[names]['data'] = data 
    data_frame_samples[names]['sampling_rate'] = sample_rate
    print("\n"+f'{names} was loaded',end="\n")
    return data_frame_samples

def time_limiters(hours,minutes,seconds):
    
    if seconds > 59:
        f_ms = int(seconds/60)
        seconds = seconds - 60
        minutes = minutes +f_ms
    if minutes > 59:
        f_hs = int(minutes/60)
        minutes = minutes -60
        hours = hours +f_hs
    return(hours,minutes,seconds)

def analyse_audios(function_inputs,keys,l):
    data_frame_samples  = function_inputs["data_frame_samples"]
    recording_data = function_inputs["recording_data"]
    results = function_inputs["results"]
    sample_rate = function_inputs["sample_rate"]
    date = function_inputs["date"]
    channel_name = function_inputs["channel_name"]
    start_time = function_inputs["start_time"]
    #error =[]
    #error = np.array(error) 

    #for keys in data_frame_samples:
    len_recording = len(recording_data)
    len_sample = len(data_frame_samples[keys]['data'])
    i = 0;
    count = 0;
    print("\n"+"analyzing: "+ str(keys))
    while(i+len_sample <= len_recording):
        corr = signal.correlate(data_frame_samples[keys]['data'],recording_data[i:i+len_sample])
        norm_corr = corr/corr.max() 
        if(np.std(norm_corr)<0.03):
            offset = (np.argmax(corr) - len(data_frame_samples[keys]['data']))/sample_rate
            count = count + 1
            results[keys]['ADDID'] = (str(keys))
            results[f'{keys}']['count'] = count
            results[f'{keys}']['off_set'].append(int(offset))
            results[f'{keys}']['Radio_Station'] = channel_name
            results[f'{keys}']['DDate'] = date
            
            start_seconds = int((i/sample_rate)-offset)
            end_seconds= int(((i+len_sample)/sample_rate)-offset)
            start_seconds = secs_to_time(start_seconds)
            end_seconds = secs_to_time(end_seconds)
            s_h = start_seconds[0]+start_time[0]
            s_m = start_seconds[1]+start_time[1]
            s_s = start_seconds[2]+start_time[2]
            s_h,s_m,s_s = time_limiters(s_h,s_m,s_s)

            e_h= end_seconds[0]+start_time[0]
            e_m = end_seconds[1]+start_time[1]
            e_s = end_seconds[2]+start_time[2]
            e_h,e_m,e_s = time_limiters(e_h,e_m,e_s)
            
            results[f'{keys}']['time_end'].append(f'{(e_h):02d}'+':'+f'{(e_m):02d}'+':'+f'{(e_s):02d}')
            results[f'{keys}']['time_start'].append(f'{(s_h):02d}'+':'+f'{(s_m):02d}'+':'+f'{(s_s):02d}')
            
            
            
            i = i+len_sample - int(offset*sample_rate)    
        else:
            #error=np.append(error,np.std(norm_corr))       
            i = i+len_sample

               
    l.update({keys : results[keys]})
def main():    
   

    recording_direct ="C:" #"C://inetpub//wwwroot//Themediatree"    #C:
    while(1):
        directory_array = [x for x in os.listdir(recording_direct+"//radiodetectionpilot")]
        if len(directory_array) > 0:
            for recording_directory in directory_array:
                print("Analyzing commercials for Radio Statio ID: "+recording_directory)
                date_time()
               
                #print("")
                
                to_check = recording_direct+"//"+"radiodetectionpilot"+"//"+recording_directory+"//"+"recordings"+"//"+"wav_out"
                wav_check = [f for f in os.listdir(to_check) if f.endswith('.mp3')]
                if not wav_check:
                    print("\n nothing in "+ recording_directory + " folder  \n")
                    TIME.sleep(10)
                    continue
                sample_directory = recording_direct+"//"+"radiodetectionpilot"+"//"+recording_directory+"//"+"sample commercials"       
                list_sample_names_mp3= [os.path.splitext(x)[0] for x in os.listdir(sample_directory) if x.endswith(".mp3")]
                list_sample_names =[os.path.splitext(x)[0] for x in os.listdir(sample_directory+"//wav_out") if x.endswith(".mp3")]
                if not (list_sample_names or list_sample_names_mp3):
                    print("\n nothin in sample commercial directory \n")
                    TIME.sleep(10)
                    continue
               
                
                recording_wav = [os.path.splitext(y)[0] for y in os.listdir(to_check) if y.endswith(".mp3")]
                
             
                
                
                lr = [sample_directory for _ in list_sample_names]
                # print(lr)
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    data = executor.map(load_audios,list_sample_names,lr)
                    data_frame_samples={}
                for datas in data:
                    #print(datas)
                    data_frame_samples={**data_frame_samples,**datas}
            
                error =[]
                error = np.array(error)  
                
                for rec in recording_wav:
                    
                    results ={}
                    for key in list_sample_names:
                        
                        results[key] = {'ADDID':"",'count':0,'off_set':[],'time_start':[],'time_end':[],'Radio_Station':[],'DDate':""}
                        
                    channel_name,date,ex = rec.split("_")
                    
                    date,time = date_time()
                    start_time= [int(x) for x in time.split(':')]
                    
                    with concurrent.futures.ProcessPoolExecutor() as executor:
                        data = executor.map(read,[to_check+"//"+rec+".mp3"])
                        
                    for test in data:
                        print(len(test))
                        sample_rate,recording_data = test
                   
                    function_inputs = {"data_frame_samples": data_frame_samples,
                                        "recording_data": recording_data,
                                        "sample_rate":sample_rate,
                                        "results": results,
                                        "channel_name": channel_name,
                                        "start_time":start_time,
                                        "date":date}
                                          
                    list_procs = list()
                    l = Manager().dict() 
                    for keys in data_frame_samples:
                           
                        p = Process(target = analyse_audios,args = (function_inputs,keys,l))
                        p.daemon =True
                        p.start()
                        list_procs.append(p)
                    for idx, w_procs in enumerate(list_procs):
                        w_procs.join()
                    #print(l)
                    results = dict(l)
                    #print(type(results))
                    
                    
                    df = pd.DataFrame(data=results)
                    ##df.index.name ='ADDID'
                    df = df.T
                    #print(df)
                    df= df[df['count'] != 0]
                    new_order = [2,0,3,6,5,1,4]
                    df = df[df.columns[new_order]]
                    
                    print("data frame \n")
                    print(df)
                    try:
                        conn = pyodbc.connect('Driver={SQL Server};'
                                            'Server=CLAUDEDEV2\SQLEXPRESS;'
                                            'Database=TheMediaTree;'
                                            'Trusted_Connection=yes;')

                        cursor = conn.cursor()

                        for row in df.itertuples():
    
                            cursor.execute('''
                                INSERT INTO TheMediaTree.dbo.AddDetected (ADDID, count, off_set, time_start, time_end, Radio_Station, DDate, file_mp3)
                                VALUES (?,?,?,?,?,?,?,?)
                                ''',
                            row.ADDID, 
                            row.count,
                            str(row.off_set),
                            str(row.time_start),
                            str(row.time_end),
                            row.Radio_Station,
                            row.DDate,
                            file_mp3               
                            )
                        conn.commit()
                        conn.close()
                    except:
                        pass
                    
                    
        else:
            TIME.sleep(60)
            #sleep or do anything
            print("nothing in array ")
            
                
if __name__==('__main__'):
    freeze_support()
    main()
    
        
        
