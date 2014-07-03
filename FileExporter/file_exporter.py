import logging
import os
import re
import shutil
import signal
import sys
from time import sleep, gmtime, strftime

from daemon import createDaemon
from simple_ftp import BasicFTPClient
from simple_sftp import BasicSFTPClient
from util import die, file_readiness_check

debug = logging.getLogger('fes').debug
info = logging.getLogger('fes').info
warning = logging.getLogger('fes').warning
error = logging.getLogger('fes').error

class FileExporter:
    def __init__(self, settings, lock_file, daemon):
        self.__settings = settings
        self.__lock_file = lock_file
        self.__daemon = daemon
        self.__sleep_interval = settings['SLEEP_INTERVAL']
        self.__staging_path = settings['STAGING_PATH']
        self.__export_path = settings['EXPORT_PATH']
        self.__method = settings['MOVE_TYPE']
        self.ftp = None
        self.sftp = None

        # Compile regexes for exludes
        self.regexes = []
        for e in settings['EXCLUDES']:
            try:
                self.regexes.append(re.compile(r'%s' % e))
            except Exception, err:
                error('There is a problem with the regex, %s' % e)
                die('There is a problem with the regex, %s' % e, err)

        self.transfer = self.get_method()

        if daemon:
            info('Launching FES daemon...')
            self.__lock_file.remove()

            retCode = createDaemon()
            if retCode == 0:
                self.runDaemon()
            else:
                die('Error creating daemon: %s (%d)' % (retCode[1], retCode[0]))
        else:
            signal.signal(signal.SIGINT, self.killProcess)
            info('Launching FES non-daemon mode...')
            info('Use CTRL-C to quit...')
            self.runLoop()

    def get_method(self):
        if self.__method == 'pull':
            return self.pullExport
        elif self.__method == 'ftp_push':
            return self.ftpExport
        elif self.__method == 'sftp_push':
            return self.sftpExport
        else:
            error('Unknown export method: %s' % self.__method)
            die('Unknown export method: %s' % self.__method)

    def runDaemon(self):
        signal.signal(signal.SIGTERM, self.killDaemon)
        info('FES daemon is now running, %s', os.getpid())
        self.__lock_file.create()

        self.runLoop()

    def killDaemon(self, signum, frame):
        debug('Recieved SIGTERM')
        info('FES daemon is shutting down')
        if self.ftp: self.ftp.close()
        if self.sftp: self.sftp.close()
        sys.exit(0)

    def killProcess(self, signum, frame):
        debug('Recieved CTRL-C')
        info('FES process is shutting down')
        if self.ftp: self.ftp.close()
        if self.sftp: self.sftp.close()
        self.__lock_file.remove()
        sys.exit(0)

    def runLoop(self):
        while True:

            with open(self.__settings['NAGIOS_ALERT'], 'w') as self.__alert_file:
                found_files = self.findFiles()
                if found_files:
                    self.transfer(found_files)
                else:
                    debug('No valid files were found.')

            self.cleanupAndSleep()

    def cleanupAndSleep(self):
        if self.__settings['DIR_CLEANUP'] == 'yes':
            debug('Searching for empty dirs at %s' % self.__staging_path)
            for (path, dirs, files) in os.walk(self.__staging_path):
                for d in dirs:
                    try:
                        os.rmdir(os.path.join(path, d))
                        debug('Removing empty dir %s' % os.path.join(path, d))
                    except Exception, e:
                        debug('Directory not empty %s, skipping...' % os.path.join(path, d))

        debug('Sleeping for %s seconds...' % self.__sleep_interval)
        sleep(float(self.__sleep_interval))

    def findFiles(self):
        debug('Searching for files at %s' % self.__staging_path)
        transfer_list = []
        for (path, dirs, files) in os.walk(self.__staging_path, topdown=True):                         
            # Not sure why I was originally editing the list in place, but I will leave it here in case I run into problems
            #files[:] = [os.path.abspath(os.path.join(path, f)) for f in files if not f.endswith('.partial') and not f.endswith('.aspx')]

            for f in files:
                if any(regex.search(f) for regex in self.regexes):
                    debug('Skipping %s' % f)
                    pass
                else:
                    transfer_list.append(os.path.join(path, f))

        if transfer_list:
            return file_readiness_check(transfer_list)
        else:
            return []

    def pullExport(self, filelist):
        # TODO: Write file to hidden file and move to visible once completed. This would be especially for
        # moving to an export_path that is acutally a network mount.

        for source in filelist:                                                                    
        
            d = re.sub(self.__staging_path, self.__export_path, source)
            destination = os.path.dirname(d)
            filename = os.path.basename(source)
        
            # Create destination path if it does not exist
            if not os.path.exists(destination):
                try:
                    debug('Destination %s does not exist, creating now...' % destination)
                    os.makedirs(destination)
                except Exception, e:
                    warning('Error creating destination: %s' % destination)
                    warning(str(e))
        
            # Remove existing file in event of an overwrite
            if os.path.exists(os.path.join(destination, filename)):
                warning('Removing existing file: %s' % filename)
                try:
                    os.remove(os.path.join(destination, filename))
                except Exception, e:
                    error('Unable to remove file %s' % filename)
                    error(str(e))
        
            try:
                info('Moving %s to %s' % (source, os.path.join(destination, filename)))
                shutil.move(source, destination)
            except Exception, e:
                error('Unable to move %s: %s' % (source, str(e)))
                self.alert('Unable to move %s' % source, str(e))

    def ftpExport(self, filelist):

        try:
            self.ftp = BasicFTPClient(self.__settings)
        except Exception, e:
            error('Unable to connect to the FTP server')
            error(str(e))
            self.alert('Unable to connect to the FTP server', str(e))
            return

        for source in filelist:

            (success, errmsg) = self.ftp.transfer_file(source)
            if success:
                try:
                    debug('Removing %s' % source)
                    os.remove(source)
                except Exception, e:
                    error('Unable to remove %s' % source)
                    error(str(e))
            else:
                self.alert('Unable to transfer the file: %s' % source, errmsg)

        self.ftp.close()
        self.ftp = None

    def sftpExport(self, filelist):

        try:
            self.sftp = BasicSFTPClient(self.__settings)
        except Exception, e:
            try:
                self.sftp.close()
            except:
                pass
            error('Unable to connect to the FTP server')
            error(str(e))
            self.alert('Unable to connect to the FTP server', str(e))
            return

        for source in filelist:

            (success, errmsg) = self.sftp.transfer_file(source)
            if success:
                try:
                    debug('Removing %s' % source)
                    os.remove(source)
                except Exception, e:
                    error('Unable to remove %s' % source)
                    error(str(e))
            else:
                self.alert('Unable to transfer the file: %s' % source, errmsg)

        self.sftp.close()
        self.sftp = None

    def alert(self, msg, err=None):
        now = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        alert_msg = now + ' - ' + msg
        if err:
            alert_msg += ' - ' + str(err)
        self.__alert_file.write(alert_msg + '\n')
