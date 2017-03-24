import configparser
import argparse
import requests
import time
import subprocess
import sys
from scans import *
import os
import zipfile

parser = argparse.ArgumentParser(description='This script records http traffic from a Selenium script to an HTD file, then kicks off a scan in AppScan Enterprise using that HTD file as explore data')
parser.add_argument("configFile", action="store", help="Relative Path to Config File e.g. myConifg.config")
args = parser.parse_args()

config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
config.read(args.configFile)

manualExplorerUrl = 'http://' + config['MANUAL_EXPLORE_SERVER']['manualexploreserverhost'] + ':' + config['MANUAL_EXPLORE_SERVER']['commandport'] + '/'
#file name will be set during stopManualExplore
htdFileName = ""

def startManualExploreServer(manualExploreServerUrl, port):
    print("Starting AppScan Presense DAST Proxy Listener: " + manualExploreServerUrl + " Port: " + str(port))
    params = {"port" : port}
    r = requests.get(manualExploreServerUrl + "automation/startproxy/" + str(port))
    print(r.text)
    if r.text.find('\"success\":true') == -1:
        return False
    else:
        print("AppScan Presense DAST Proxy is now listening")
        return True

def stopManualExploreServer(manualExploreServerUrl, port, HAR2HTD_location):
    # stop DAST Proxy
    print("Stopping AppScan Presense DAST Proxy...", end="", flush=True)
    r = requests.get(manualExploreServerUrl + "automation/stopproxy/" + str(port))
    #print(r.text)
    #check response for success
    if r.text.find('\"success\":true') == -1:
        return False
    else:
        print("  --Proxy Stopped")

    #issue request to download the traffic file
    print("Retrieving traffic data...")
    r = requests.get(manualExploreServerUrl + 'automation/traffic/' + str(port))
    
    #traffic file will be a .zip file, so need to download it first -- need to add error checking
    traffic_file_name = 'traffic.zip'
    traffic_file = open(traffic_file_name, "wb")
    for chunk in r.iter_content(chunk_size=1024):
        if chunk:
            traffic_file.write(chunk)
    traffic_file.close()

    # and next unzip it, a directory called traffic will hold the .har file -- need to add error checking
    z = zipfile.ZipFile(traffic_file_name, 'r')
    z.extractall('traffic')
    z.close()
    HAR_file_name = 'traffic\\' + z.filelist[0].filename
    HTD_file_name = HAR_file_name.replace('.har','.htd')

    print("Saved HAR File: " + HAR_file_name)

    # now convert the .har to htd -- need to add error checking
    print("Converting HAR to HTD")
    cmd = subprocess.run(HAR2HTD_location + 'HAR2HTD.exe ' + HAR_file_name + ' ' + HTD_file_name, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    if(cmd.returncode != 0):
        print("HAR2HTD Process was terminated")
        HTD_file_name = ""
    else:
        print("HAR2HTD successfully converted file")

    return HTD_file_name

#kils a process if running e.g. processKill('ManualExploreServer.exe')
def processKill(procName):
    cmd = subprocess.run('c:\windows\system32\cmd.exe /c c:\windows\system32\TASKKILL.exe /F /IM ' + procName, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    if(cmd.returncode == 0):
        print("Process " + procName + " was terminated")

def writeBlankConfig():
    blank_config = configparser.ConfigParser()
    blank_config['MANUAL_EXPLORE_SERVER'] = {}
    blank_config['MANUAL_EXPLORE_SERVER']['manualexploreserverhost'] = "appscanvm"
    blank_config['MANUAL_EXPLORE_SERVER']['commandPort'] = "9999"
    blank_config['MANUAL_EXPLORE_SERVER']['listeningport'] = "19995"
    blank_config['MANUAL_EXPLORE_SERVER']['ME_location'] = "c:\\ASOC\\AppScanPresence-Win_x86_64\\Automation\\"
    blank_config['MANUAL_EXPLORE_SERVER']['HAR2HTD_location'] = "c:\\HAR2HTD\\HAR2HTD Release\\"

    blank_config['SELENIUM'] = {}
    blank_config['SELENIUM']['scriptCmd'] = "mySeleniumScript.py"

    blank_config['APPSCAN'] = {}
    blank_config['APPSCAN']['templatename'] = "template name"
    blank_config['APPSCAN']['startingurl'] = "http://demo.testfire.net"
    blank_config['APPSCAN']['testusername'] = "jsmith"
    blank_config['APPSCAN']['testpassword'] = "demo1234"
    blank_config['APPSCAN']['scanjobname'] = "scan job name"
    blank_config['APPSCAN']['appid'] = "100"
    blank_config['APPSCAN']['foldername'] = "Automation"
    new_config_file = open("configTemplate.config", "w")
    blank_config.write(new_config_file)

print("===== Starting DAST Automation =====")

print('Start the AppScan Presense DAST Proxy')

#kill old manual explore server instance if it is running
#processKill("ManualExploreServer.exe")

#time.sleep(3)

#start the manual explore server process
mesProc = subprocess.Popen(["node", config['MANUAL_EXPLORE_SERVER']['ME_location'] + "app.js", config['MANUAL_EXPLORE_SERVER']['commandPort']], stdout=subprocess.DEVNULL)

time.sleep(5)
print("AppScan Presense DAST Proxy: PID " + str(mesProc.pid))

#start manual explore server listener
if(startManualExploreServer(manualExplorerUrl, config['MANUAL_EXPLORE_SERVER']['listeningport']) == False):
    sys.exit('Manual Explore Server Not Running. Exiting')
    
time.sleep(10)

#run Selenium Script
print("Running Selenium Script: " + config['SELENIUM']['scriptCmd'])
completedProc = subprocess.run(config['SELENIUM']['scriptCmd'], universal_newlines=True, stdout=subprocess.PIPE)
print("Selenium Script Done")
print("Selenium Script Return Code: " + str(completedProc.returncode))
print(completedProc.stdout)

#stop manual explore server and save htd file
htdFileName = stopManualExploreServer(manualExplorerUrl, config['MANUAL_EXPLORE_SERVER']['listeningport'], config['MANUAL_EXPLORE_SERVER']['HAR2HTD_location'])
if(htdFileName.find(".htd") == -1):
    sys.exit('Something went wrong stopping the manual explore server. Exiting')

time.sleep(5)
mesProc.terminate()

#Create a server object
server=ase()
server.setServer('https://appscanvm/ase') #Set the url for the enterprise server, don't end with a / 
server.logIn('appscanvm\Administrator','watchfire') #Set the user name and password, and log in
templateId = 0
folderName = config['APPSCAN']['foldername']
templateName = config['APPSCAN']['templatename']
scanName = config['APPSCAN']['scanjobname']
scanFolderId = '0'
appId = config['APPSCAN']['appid']
startingUrl = config['APPSCAN']['startingurl']
testUser = config['APPSCAN']['testusername']
testPassword = config['APPSCAN']['testpassword']

print('Check to see if folder ' + folderName + ' exists')

scanFolderId = server.findFolderByName(folderName)
if(scanFolderId == -1):
    sys.exit('Cannot find folder: ' + folderName + '. Exiting')

print('Folder Found ID: ' + scanFolderId)
print('Checking to see if scan ' + scanName + ' already exists in folder ' + folderName)

scanJobId = server.verifyFolderItemExists(scanName, scanFolderId)
reportPackId = server.verifyFolderItemExists(scanName, scanFolderId, 1)

if(scanJobId == 0):
    print("Not Found. We must create scan from template " + templateName)
    print('Looking for Scan Teamplate: ' + templateName)

    templates = server.getTemplatesList()
    
    for t in templates:
        if(templates[t] == templateName):
            print("Found! Template ID: " + t)
            templateId = t
    if(templateId == 0):
        sys.exit("Template Not Found...Exiting")
    
    print('Create Scan from Template ' + str(templateId))
    r = server.createScan(scanName,'Automated Scan from Jenkins - Based on Selenium Traffic', str(templateId), scanFolderId, appId)
    time.sleep(5)
    scanJobId = server.verifyFolderItemExists(scanName, scanFolderId)
    reportPackId = server.verifyFolderItemExists(scanName, scanFolderId, 1)
    if(scanJobId == 0):
       sys.exit('Scan did not exist and we cannot create one! Exiting')

print(scanName + " already exists")
print('Using Scan Job ' + str(scanJobId))
print('Uploading HTD...', end="", flush=True)
r=server.uploadHTD('./'+htdFileName, str(scanJobId))
print("done")

print("Deleting HTD File: " + htdFileName)
os.remove(htdFileName)

#set start URL here
print('Adding starting URL: ' + startingUrl)
server.changeURL(scanJobId, startingUrl)

#set login type to automatic
print("Setting login type to Automatic")
server.changeLoginType(scanJobId, '3')

#set credentials here
print('Adding test credentials: ' + testUser + "/" + testPassword)
server.changeCredentials(scanJobId,testUser,testPassword)

print('Running Scan Job')
#Run scan job
#server.runTask('Scan',str(scanJobId),15) 

if(reportPackId == 0):
       sys.exit('Report Pack Not Found... Exiting')

print('Wait for reports to update')
#Wait for reports to update
server.runTask('Results update',str(reportPackId),15) 

#Utility for setting various color is the html table
def color(x):
    return {
        0: "FF0000",
        1: "FF9100",
		2: "FFE600",
		3: "E7E7E7",
		4: "FFB2B2",
		5: "CCFFCC",
		6: "FFFFCC",
        }.get(x, "E7E7E7") 


#Getting report details
print('Getting Report Details')
reports = server.getReportPackList(str(reportPackId))
secIssuesReportId = 0
for r in reports:
    if(reports[r] == 'Security Issues'):
        secIssuesReportId = r
        print('Security Issues Report Found: RID ' + str(r))

issueCount = server.getIssueCount(str(secIssuesReportId))



print()
print(" - Security Issues - ")
print("Critical: " + str(issueCount['Critical']))
print("High: " + str(issueCount['High']))
print("Medium: " + str(issueCount['Medium']))
print("Low: " + str(issueCount['Low']))
print("Information: " + str(issueCount['Information']))

#Create a monkit chart
monkit='<categories>\n<category name="Security findings" scale="No. of Findings">\n<observations>\n'
monkit+='<observation name="Critical">'+str(issueCount['Critical'])+'</observation>\n'
monkit+='<observation name="High">'+str(issueCount['High'])+'</observation>\n'
monkit+='<observation name="Medium">'+str(issueCount['Medium'])+'</observation>\n'
monkit+='<observation name="Low">'+str(issueCount['Low'])+'</observation>\n'
monkit+='<observation name="Information">'+str(issueCount['Information'])+'</observation>\n'
monkit=monkit+'</observations>\n</category>\n</categories>'

f = open('monkit.xml', 'w')
f.write(monkit)
f.close();

server.endSession()
print()
print("Exceptions Caught: " + str(server.connectionErrors))
print("===== End DAST Automation =====")


