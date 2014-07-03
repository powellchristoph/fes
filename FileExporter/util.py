import hashlib
import sys
import os
import time
import logging

from ConfigParser import SafeConfigParser

debug = logging.getLogger('util').debug

def setup_logging(settings, enable_debug, daemon):
    if daemon:
        daemon_log = settings['DAEMON_LOG']
        if daemon_log:
            fh = logging.FileHandler(daemon_log, 'a')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logging.getLogger().addHandler(fh)
            if enable_debug:
                logging.getLogger().setLevel(logging.DEBUG)
            else:
                logging.getLogger().setLevel(logging.INFO)

            info = logging.getLogger('fes').info
            info('FES launched with the following config options:')
            info('    %s', ' '.join(sys.argv))
            for k,v in settings.iteritems():
                info('    %s: %s' % (k, v))
    else: # Non-daemon
        logging.basicConfig(format="%(message)s")

        debug = logging.getLogger('fes').debug
        info = logging.getLogger('fes').info

        if enable_debug:
            logging.getLogger().setLevel(logging.DEBUG)
            debug('Debug mode enabled')
            for k,v in settings.iteritems():
                info('    %s: %s' % (k, v))
        else:
            logging.getLogger().setLevel(logging.INFO)

def read_config(config_file):
    settings = {}

    # Read the config file
    if not os.path.exists(config_file):
        die('Config file does not exist: %s' % config_file)

    parser = SafeConfigParser()
    parser.read(config_file)
    section = 'fes'
 
    try:
        settings['MOVE_TYPE'] = parser.get(section, 'MOVE_TYPE')
        settings['STAGING_PATH'] = parser.get(section, 'STAGING_PATH')
        settings['EXPORT_PATH'] = parser.get(section, 'EXPORT_PATH')
        settings['LOCK_FILE'] = parser.get(section, 'LOCK_FILE')
        settings['SLEEP_INTERVAL'] = parser.get(section, 'SLEEP_INTERVAL')
        settings['DAEMON_LOG'] = parser.get(section, 'DAEMON_LOG')
        settings['NAGIOS_ALERT'] = parser.get(section, 'NAGIOS_ALERT')
    except Exception, e:
        die('Error in the configuration file.', e)

    if parser.has_option(section, 'DIR_CLEANUP'):
        settings['DIR_CLEANUP'] = parser.get(section, 'DIR_CLEANUP')
    else:
        settings['DIR_CLEANUP'] = 'yes'

    if parser.has_option(section, 'EXCLUDES'):
        settings['EXCLUDES'] = parser.get(section, 'EXCLUDES').split(',')
        settings['EXCLUDES'] = [e.strip('"') for e in settings['EXCLUDES']]
    else:
        settings['EXCLUDES'] = []
 
    if settings['MOVE_TYPE'] == 'ftp_push':
        try:
            settings['USERNAME'] = parser.get(section, 'USERNAME')
            settings['PASSWORD']= parser.get(section, 'PASSWORD')
            settings['FTP_SERVER'] = parser.get(section, 'FTP_SERVER')
            if parser.has_option(section, 'DESTINATION'):
                settings['DESTINATION'] = parser.get(section, 'DESTINATION')
            else:
                settings['DESTINATION'] = None
        except Exception, e:
            die('You must set username/password/ftp_server if you use ftp_push', e)

    if settings['MOVE_TYPE'] == 'sftp_push':
        try:
            settings['USERNAME'] = parser.get(section, 'USERNAME')
            settings['PASSWORD']= parser.get(section, 'PASSWORD')
            settings['FTP_SERVER'] = parser.get(section, 'FTP_SERVER')
            settings['SSH_PORT'] = int(parser.get(section, 'SSH_PORT'))
            if parser.has_option(section, 'DESTINATION'):
                settings['DESTINATION'] = parser.get(section, 'DESTINATION')
            else:
                settings['DESTINATION'] = None
        except Exception, e:
            die('You must set username/password/ftp_server/ssh_port if you use ftp_push', e)

    return settings

def die(msg, ex=None):
    print msg
    if ex: print ex
    sys.exit(1)

def get_last_byte(filename):
    # Update to use with statement once Centos updates its python version
    f = open(filename, 'rb')
    f.seek(0, 2)
    b = f.tell()
    f.close()
    return b

def hashfile(filename, length=16*1024):
    fsrc = open(filename, 'rb')
    hasher = hashlib.md5()
    while 1:
        buf = fsrc.read(length)
        if not buf:
            break
        hasher.update(buf)
    return hasher.digest()

def file_readiness_check(filelist, check_type=0, delay=10):
    """
    filelist must contain abspaths. 

    Check types are: 
            consecutive seek = 0
            MD5 Hash         = 1
            Date/Time/Size   = 2

    Returns a list of files that are ready.
    """

    ready_file_list = []
    tmp = {}

    # Set the check_type function
    if check_type == 0:
        check = get_last_byte
    elif check_type == 1:
        check = hashfile
    elif check_type == 2:
        raise Exception('Date/Time/Size check not implemented.')
    else:
        raise Exception('Unknown check type.')

    for filename in filelist:
        if not os.path.exists(filename):
            continue
        tmp[filename] = check(filename)

    time.sleep(delay)

    for filename in filelist:
        if not os.path.exists(filename):
            continue
        result = check(filename)
        if tmp[filename] == result:
            ready_file_list.append(filename)

    return ready_file_list
