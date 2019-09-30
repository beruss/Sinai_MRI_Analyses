#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 08:23:46 2019

@author: bruss
"""

import numpy as np
import os
import shutil
import pandas as pd
import pydicom
import shlex
import subprocess
#%%
dcmWarehouse="/projects/bruss/Sinai/DICOM/"
bidsWarehousePath="/projects/bruss/Sinai/BIDS_data/"
temp_DicomToBids="/projects/bruss/Sinai/temp/"

monkeyNames=["Lafeyette"]

    
#%%
if __name__ == '__main__':
    #%%
    subjectsAlreadyConvertedToBids=np.genfromtxt(bidsWarehousePath+"/Subjects_Converted_Monkey.csv",
                                                     delimiter=",",dtype=str)
    todaysWarehouseDicoms=[monkey for monkey in os.listdir(dcmWarehouse) 
                               if monkey.startswith(tuple(monkeyNames)) ]
    
    newParticipantsDF=pd.read_table(bidsWarehousePath+'/participants.tsv',header=None)
    subExistingList=np.array(newParticipantsDF.iloc[:,0],dtype=str)
    newParticipantsDF2=np.array(newParticipantsDF,dtype=str)
    
    #%%
    for subjectFolder in os.listdir(dcmWarehouse):
        if subjectFolder in subjectsAlreadyConvertedToBids:
            continue
        elif subjectFolder not in todaysWarehouseDicoms:
            continue
 
        print(subjectFolder)
        break

        subjectID=[monkey for monkey in monkeyNames if subjectFolder[0:4] in monkey]
        subjectID=subjectID[0]
        print(subjectID)
        subjectSession=subjectFolder[-8:]
        subjectFolderPath=dcmWarehouse+subjectFolder
        bidsFormatDicomPath=bidsWarehousePath+subjectID
          
        subjectLevel=dcmWarehouse+subjectFolder
        
        for Scan in os.listdir(subjectLevel): 
#            modalityFound=False
            ScanLevel=subjectLevel+"/"+Scan + "/DICOM"
            print(Scan)
        
            for dicom in os.listdir(ScanLevel):
                newDicomPath=ScanLevel+"/"+dicom
                print(newDicomPath)
#                call_System_dcmodify(Scan,newDicomPath)
                dicomOne=pydicom.dcmread(newDicomPath)
                supineOrProne=dicomOne.PatientPosition
                print(supineOrProne)
                break
            break
        createSessionFolder(subjectFolderPath,subjectSession,subjectID,
                                temp_DicomToBids)
        
        protocolInTemp=temp_DicomToBids+"Protocol_Translator.json"
        if os.path.exists(protocolInTemp):
            os.remove(protocolInTemp)      
        
        ##FIRST PASS of dcm2bids --- creates conv dir without correct file names 
        os.system("/home/bruss/anaconda3/bin/python /projects/bruss/BIDS_pipe/dcm2bids.py -i "+ temp_DicomToBids +" -o "+ bidsWarehousePath)    
        
        jasonFilePath= dcmWarehouse+"Protocol_Translator.json"
        shutil.copyfile(jasonFilePath,protocolInTemp)
        
        ## FIX SERIES DESCRIPTIONS in file names to match Protocol Translator
        SubjSesBIDs_dir=bidsWarehousePath+'/sub-'+subjectID+'/ses-'+subjectSession +'/conv/'
        RenameScans(SubjSesBIDs_dir)
            
        ##SECOND PASS of dcm2bids 
        os.system("/home/bruss/anaconda3/bin/python /projects/bruss/BIDS_pipe/dcm2bids.py -i "+ temp_DicomToBids +" -o "+ bidsWarehousePath)    
        
        os.remove(protocolInTemp)
        print ("Converted Second Pass")
        
        #Save to The DCM warehouse and to the Temporal just in case
        df=pd.DataFrame([subjectFolder])
        with open(bidsWarehousePath+"/Subjects_Converted_Monkey.csv", 'a') as existingBidsSubjects:
            df.to_csv(existingBidsSubjects, header=False,index=False)
        temp_DcmSubject=temp_DicomToBids+"/"+subjectID
        shutil.rmtree(temp_DcmSubject)
        
        monkeyName="sub-%s"%subjectID
        monkeySess="ses-%s"%subjectSession
        monkeyBIDS='/'.join([bidsWarehousePath[0:-1],monkeyName,monkeySess])
        
        scanTypes=[mod for mod in os.listdir(monkeyBIDS)] # (if not "dwi" in mod) was formerly in code
        if supineOrProne=="HFP":
            for sType in scanTypes:
                scanPath='/'.join([monkeyBIDS,sType])
                niiList=[nii for nii in os.listdir(scanPath) if nii.endswith(".nii.gz")]
                for nifti in niiList:
                    niiPath='/'.join([scanPath,nifti])                        
                    if sType=="func" or sType=="fmap": 
                        refit="/opt/afni/3drefit -deoblique -orient RAS %s"%niiPath
                    elif sType=="anat": 
                        refit="/opt/afni/3drefit -deoblique -orient LAS %s"%niiPath
                    print(refit)
                    args=shlex.split(refit)
                    subprocess.call(args)
        # 3dresample to RPI each of the scans
        for sType in scanTypes:
            scanPath='/'.join([monkeyBIDS,sType])
            niiList=[nii for nii in os.listdir(scanPath) if nii.endswith(".nii.gz")]
            for nifti in niiList:
                niiPath='/'.join([scanPath,nifti])  
                newNiiPath=niiPath[:-7]+"2"+niiPath[-7:]
                shutil.move(niiPath,newNiiPath)
                resample="/opt/afni/3dresample -inset %s -prefix %s -orient RPI"%(newNiiPath,niiPath)
                print(resample)
                args=shlex.split(resample)
                subprocess.call(args)
                os.system("rm -rf %s"%newNiiPath)
        break
  
#%%
def RenameScans(SubjSesBIDs_dir):
    ## FIX SERIES DESCRIPTIONS
    
    for Scan in os.listdir(SubjSesBIDs_dir):
        print(Scan)
        connector = '--'
        splitScan = Scan.split('.')
        vals = splitScan[0].split(connector)
        if len(vals) < 4:
            splitScan[0] ='.'.join(splitScan[0:2])
            splitScan.pop(1)
            vals = splitScan[0].split(connector)
            
        vals[1] = vals[1] + '_' + vals[3]
        curScan = SubjSesBIDs_dir + Scan
        if len(splitScan) > 2:
            newScan = SubjSesBIDs_dir+connector.join(vals)+'.'+ splitScan[1]+'.'+splitScan[2]
        else:
            newScan = SubjSesBIDs_dir + connector.join(vals) + '.' + splitScan[1]
        print(newScan)
        os.rename(curScan,newScan)
        
#%%    
def createSessionFolder(subjectFolderPath,subjectSession,subjectID,temp_DicomToBids):
    """ Create a temporary folder structure needed to convert to bids
        as well as the Protocol Translator configuration file that 
        has all the modalities for each session
     """
    #%%
    temp_DcmSubject=temp_DicomToBids+"/"+subjectID
    if not os.path.exists(temp_DcmSubject):
        os.makedirs(temp_DcmSubject)
    sessionFolderPath=temp_DcmSubject+"/"+subjectSession
    if not os.path.exists(sessionFolderPath):
        os.makedirs(sessionFolderPath)
    t1wCount,t1wVar=0,0
    t2wCount,t2wVar=0,0
    fGradCount,fGradVar=0,0
    rGradCount,rGradVar=0,0
    boldCount,boldVar=0,0
    dwiCount,dwiVar=0,0
    
    protocol_file = open( dcmWarehouse+"/Protocol_Translator.json", "w")
    protocol_file.write('{\n')

    # Count the number of modalities with multiple Runs
    for eachModality in os.listdir(subjectFolderPath):
        if "T1w_MPR_0.5" in eachModality or "mp2rage" in eachModality:
            t1wCount+=1     
        elif "T2w_SPC_0.5" in eachModality:
            t2wCount+=1
        elif "BOLD_MB2_PAT2_HF" in eachModality:
            rGradCount+=1
        elif "BOLD_MB2_PAT2_FH" in eachModality:
            boldCount+=1
        elif "DWI_LR" in eachModality or "DWI_LR" in eachModality:
            dwiCount+=1

    # Build the protocol translator json file for the bids conversion
    for eachModality in os.listdir(subjectFolderPath):
        modality_parts = eachModality.split('_')
        modality_parts.append(modality_parts.pop(0))
        New_Mod_Name = '_'
        New_Mod_Name=New_Mod_Name.join(modality_parts)
        print(eachModality)
        print(New_Mod_Name)
        
        if "T1w_MPR_0.5" in eachModality or "mp2rage" in eachModality:
            t1wVar+=1
            if t1wCount>1: protocol_file.write(f'"{New_Mod_Name}":["anat","run-{t1wVar}_T1w"],\n') 
            else: protocol_file.write(f'"{New_Mod_Name}":["anat","T1w"],\n') 
        elif "T2w_SPC_0.5" in eachModality:
            t2wVar+=1
            if t2wCount>1: protocol_file.write(f'"{New_Mod_Name}":["anat","run-{t2wVar}_T2w"],\n') 
            else: protocol_file.write(f'"{New_Mod_Name}":["anat","T2w"],\n')
        elif "BOLD_MB2_PAT2_HF" in eachModality:
            rGradVar+=1
            if rGradCount>1: protocol_file.write(f'"{New_Mod_Name}":["fmap","run-{rGradVar}_magnitude2"],\n')
            else: protocol_file.write(f'"{New_Mod_Name}":["fmap","magnitude2"],\n')
        elif "BOLD_MB2_PAT2_FH" in eachModality:
            boldVar+=1
            if boldCount>1: protocol_file.write(f'"{New_Mod_Name}":["func","task-REST_run-{boldVar}_bold"],\n') 
            else: protocol_file.write(f'"{New_Mod_Name}":["func","task-REST_bold"],\n')  
        elif "DWI_LR" in eachModality or "DWI_RL" in eachModality :
            dwiVar+=1
            if "RL" in eachModality:
                if dwiCount>1: protocol_file.write(f'"{New_Mod_Name}":["dwi","acq-RL_run-{dwiVar}_dwi"],\n') 
                else: protocol_file.write(f'"{New_Mod_Name}":["dwi","acq-RL_dwi"],\n') 
            else:
                if dwiCount>1: protocol_file.write(f'"{New_Mod_Name}":["dwi","acq-LR_run-{dwiVar}_dwi"],\n') 
                else: protocol_file.write(f'"{New_Mod_Name}":["dwi","acq-LR_dwi"],\n') 
        else: pass
           
        if eachModality!=subjectSession and "gre_" not in eachModality and "localizer" not in eachModality:
            oldModalityPath=subjectFolderPath+"/"+eachModality+"/DICOM"
            newModalityPath=sessionFolderPath+"/"+New_Mod_Name
            #print (newModalityPath)
            if not os.path.exists(newModalityPath):
                shutil.copytree(oldModalityPath,newModalityPath)
            
    protocol_file.write(f'"LAST_SCAN":["anat","LAST_SCAN"]\n') 
    protocol_file.write("}")
    protocol_file.close()