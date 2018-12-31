import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import datetime
import re as regex
import smtplib
from email.mime.text import MIMEText
import enum

# setup for logfile and IP store
data_folder = Path('FOLDERPATH')
logFile = 'ipLog.txt'
ipFile = 'ipFile.txt'
KEYAUTH = 'KEY'
HOSTNAME = 'DOMAIN'
ALLHOST = 'all'

# creating enumerations using class 
class DebugCategory(enum.Enum):
    INFO = 1
    DEBUG = 2
    ERROR = 3

def main():
    # check if files exist
    if not (data_folder.joinpath(logFile)).exists():
        error_text = ('{} {}: {}\n'.format(DebugCategory.DEBUG.name, datetime.datetime.now(), "LogFile does not exist"))
        print(error_text)
        sys.exit(error_text)
    if not (data_folder.joinpath(ipFile)).exists():
        error_text = ('{} {}: {}\n'.format(DebugCategory.DEBUG.name, datetime.datetime.now(), "IpFile does not exist"))
        print(error_text)
        sys.exit(error_text)

    # get current IP
    request = Request('https://www.ddnss.de/meineip.php')
    try:
        contents = urlopen(request).read()
    except HTTPError as e:
        Log(DebugCategory.ERROR, e.code)
        Log(DebugCategory.ERROR, e.read())
    except URLError as e:
        Log(DebugCategory.ERROR, e.reason)
    except:
        Log(DebugCategory.ERROR, 'Unexpected error: {}'.format(sys.exc_info()[0]))
    else:
        newIp = regex.search('(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', str(contents)).group(0)

        if newIp == None:
            Log(DebugCategory.ERROR, 'No IP found in HTTP response')

        # compare stored IP with received IP, update if necessary
        with open(data_folder / ipFile, 'r') as ipFileFile:
            oldIp = ipFileFile.read().strip('\n\r')  # read() adds a newline char to the end

        if oldIp != newIp:
            # update IP
            request = Request('https://www.ddnss.de/upd.php?key={}&host={}&host={}'.format(KEYAUTH, HOSTNAME, ALLHOST))
            try:
                contents = urlopen(request).read()

            except HTTPError as e:
                Log(DebugCategory.ERROR, e.code)
                Log(DebugCategory.ERROR, e.read())
            except URLError as e:
                Log(DebugCategory.ERROR, e.reason)
            except:
                Log(DebugCategory.ERROR, 'Unexpected error: {}'.format(sys.exc_info()[0]))
            else:
                # check update response
                if regex.search('(Updated \d+ hostname.)', str(contents)):
                    Log(DebugCategory.INFO, 'Update successful. Old IP {}, New IP {}\n'.format(oldIp, newIp))

                    with open(data_folder / ipFile, 'w') as ipFileFile:
                        ipFileFile.write('{}\n'.format(newIp))
                else:
                    Log(DebugCategory.ERROR, 'Update failed!')
                    parts = regex.findall('>([^<>\\\\]+)<', str(contents))
                    message = ''
                    for line in parts:
                        message += ('{}\n'.format(line))
                    Log(DebugCategory.ERROR, message)
        else:
            Log(DebugCategory.INFO, 'IP did not change {}'.format(oldIp))


def Log(category, message):
    errorText = category.name + ' {}:'.format(datetime.datetime.now())
    message = str(message)
    if '\n' in message:
        message = message.strip('\n\r').replace('\n', '\n' + len(errorText) * ' ')
    # if '\\n' in message:
        # message = message.strip('\n\r').replace('\\n', '\n' + len(errorText) * ' ')
        # message = message.replace('\\t', '\t')
    errorText += message
    with open(data_folder / logFile, 'a') as logfile:
        logfile.write(errorText + '\n')
    if category == DebugCategory.ERROR:
        try:
            SendMail(errorText)
        except:
            with open(data_folder / logFile, 'a') as logfile:
                logfile.write('ERROR {}: Sending mail failed\n'.format(datetime.datetime.now()))

def SendMail(text):
    try:
        server = smtplib.SMTP('mail.gmx.net', 587)
        server.starttls()
        server.login("USER", "PASSWORD")

        recipients = 'rec'
        sender = 'sen'

        msg = MIMEText(text)
        msg['Subject'] = 'DDNSS-Updater Error Report'
        msg['From'] = sender
        msg['To'] = recipients

        server.send_message(msg, sender, recipients)
    except:
        Log(DebugCategory.DEBUG, sys.exc_info()[0])

if __name__ == '__main__':
    main()
