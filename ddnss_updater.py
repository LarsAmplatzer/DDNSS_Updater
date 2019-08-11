import sys
from pathlib import Path
import configparser
import socket
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import datetime
import re as regex
import smtplib
from email.mime.text import MIMEText
import enum

# setup for logfile and IP store
config = configparser.ConfigParser()

# creating enumerations using class
class DebugCategory(enum.Enum):
    INFO = 1
    DEBUG = 2
    ERROR = 3


def main():
    # load config file    
    configfile = sys.argv[1]
    if not Path(configfile).exists():
        error_text = ('{} {}: {}\n'.format(DebugCategory.DEBUG.name, datetime.datetime.now(), "Config file does not exist"))
        print(error_text)
        sys.exit(error_text)
        
    LoadConfiguration(configfile)
    
    # check if files exist    
    if not Path(logFile).exists():
        error_text = ('{} {}: {}\n'.format(DebugCategory.DEBUG.name, datetime.datetime.now(), "LogFile does not exist"))
        print(error_text)
        sys.exit(error_text)
    if not Path(ipFile).exists():
        error_text = ('{} {}: {}\n'.format(DebugCategory.DEBUG.name, datetime.datetime.now(), "IpFile does not exist"))
        print(error_text)
        sys.exit(error_text)
    
    # check if DNS service is available
    if(is_connected('www.ddnss.de') == False)
        Log(DebugCategory.ERROR, 'DNS service', 'DNS service not reachable -> www.ddnss.de')
        sys.exit()

    # get current IP
    request = Request('https://www.ddnss.de/meineip.php'):
    try:
        contents = urlopen(request).read()
    except HTTPError as e:
        Log(DebugCategory.ERROR, 'HTTPError in urlopen() for {}'.format(request.full_url), e.code)
        Log(DebugCategory.DEBUG, 'HTTPError in urlopen() for {}'.format(request.full_url), e.read())
    except URLError as e:
        Log(DebugCategory.ERROR, 'URLError in urlopen() for {}'.format(request.full_url), e.reason)
    except:
        Log(DebugCategory.ERROR, 'General error in urlopen for {}'.format(request.full_url), 'Unexpected error: {}'.format(sys.exc_info()[0]))
    else:
        newIp = regex.search('(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', str(contents)).group(0)       # search for a text that looks like an IP

        if newIp is None:
            Log(DebugCategory.ERROR,"newIp", 'No IP found in HTTP response')

        # compare stored IP with received IP, update if necessary
        with open(ipFile, 'r') as ipFileFile:
            oldIp = ipFileFile.read().strip('\n\r')  # read() adds a newline char to the end

        if oldIp != newIp:
            # update IP
            request = Request('https://www.ddnss.de/upd.php?key={}&host={}&host={}'.format(KEYAUTH, HOSTNAME, ALLHOST))
            try:
                contents = urlopen(request).read()

            except HTTPError as e:
                Log(DebugCategory.ERROR, 'HTTPError in urlopen() for {}'.format(request.full_url), e.code)
                Log(DebugCategory.DEBUG, 'HTTPError in urlopen() for {}'.format(request.full_url), e.read())
            except URLError as e:
                Log(DebugCategory.ERROR, 'URLError in urlopen() for {}'.format(request.full_url), e.reason)
            except:
                Log(DebugCategory.ERROR, 'General error in urlopen for {}'.format(request.full_url), 'Unexpected error: {}'.format(sys.exc_info()[0]))
            else:
                # check update response
                if regex.search('(Updated \d+ hostname.)', str(contents)):
                    Log(DebugCategory.INFO, 'IP update', 'Update successful. Old IP {}, New IP {}\n'.format(oldIp, newIp))
                    SendMail('DDNSS-Updater IP update report', 'IP address for {} changed from {} to {}'.format(HOSTNAME, oldIp, newIp))
                    with open(ipFile, 'w') as ipFileFile:
                        ipFileFile.write('{}\n'.format(newIp))
                else:
                    Log(DebugCategory.ERROR, 'Update failed!', 'Could not finde a valid IP address in response')
                    parts = regex.findall('>([^<>\\\\]+)<', str(contents))      # Regex: "([^<>\\]+)", only take text that does not contain <,> or \. Result is only HTML content that would be displayed to the user in a browser
                    message = ''
                    for line in parts:
                        message += ('{}\n'.format(line))
                    Log(DebugCategory.ERROR, 'Response details', message)
        else:
            Log(DebugCategory.INFO, 'IP status', 'IP did not change {}'.format(oldIp))


def Log(category, hint, message):
    message = str(message)
    if '\n' in message:
        message = message.strip('\n\r').replace('\n', '\n' + len(errorText) * ' ')
    errorText = category.name + ' {}: '.format(datetime.datetime.now()) + hint + ': ' + message 
    with open(logFile, 'a') as logfile:
        logfile.write(errorText + '\n')
    if category == DebugCategory.ERROR:
        try:
            SendMail('DDNSS-Updater error report', errorText)
        except:
            with open(logFile, 'a') as logfile:
                logfile.write('ERROR {}: Sending mail failed\n'.format(datetime.datetime.now()))


def SendMail(subject, text):
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(mail_user, mail_password)

        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient

        server.send_message(msg, sender, recipient)
    except:
        Log(DebugCategory.DEBUG, 'Sending mail', sys.exc_info()[0])

def is_connected(remote):
  try:
    host = socket.gethostbyname(remote)
    s = socket.create_connection((host, 80), 2)
    return True
  except:
     pass
  return False

def LoadConfiguration(configfile):
    config.read(configfile)    
    
    global data_folder
    global logFile
    global ipFile
    global KEYAUTH
    global HOSTNAME
    global ALLHOST

    global smtp_port
    global smtp_server
    global mail_user
    global mail_password

    global recipient
    global sender
    
    logFile = config.get('LOGGING', 'logfile')
    ipFile = config.get('LOGGING', 'ipfile')

    KEYAUTH = config.get('BUSINESS', 'authentication_key')
    HOSTNAME = config.get('BUSINESS', 'hostname')
    ALLHOST = config.get('BUSINESS', 'allhost')

    smtp_port = config.get('MAIL', 'smtp_port')
    smtp_server = config.get('MAIL', 'smtp_server')
    mail_user = config.get('MAIL', 'user')
    mail_password = config.get('MAIL', 'password')
    recipient = config.get('MAIL', 'recipient')
    sender = config.get('MAIL', 'sender')

if __name__ == '__main__':
    main()
