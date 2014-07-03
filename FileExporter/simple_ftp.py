import ftplib
import logging
import os
import re

debug = logging.getLogger('fes').debug
info = logging.getLogger('fes').info
warning = logging.getLogger('fes').warning
error = logging.getLogger('fes').error

class BasicFTPClient():

    def __init__(self, settings):
        self.__username = settings['USERNAME']
        self.__password = settings['PASSWORD']
        self.__server = settings['FTP_SERVER']
        self.__staging_path = settings['STAGING_PATH']
        if settings['DESTINATION']:
            self.destination = settings['DESTINATION']
        else:
            self.destination = None
        self.is_active = False
        debug('Creating FTP session to %s with %s/%s' % (self.__server, self.__username, self.__password))

        self.connect()

    def connect(self):
        # Create FTP session
        self.ftp = ftplib.FTP(self.__server, timeout=10)
        self.ftp.login(self.__username, self.__password)
        self.is_active = True
        # Sets the docroot, some FTP servers do not properly chroot the account into a home dir
        # so we manually set it here, just in case
        self.__docroot = os.path.join(self.ftp.pwd(), self.destination)

    def create_path(self, filename):

        if self.__staging_path != os.path.dirname(filename):
            r = re.sub(self.__staging_path, '', os.path.dirname(filename))
            dirs = filter(None, r.split('/'))
            path = self.__docroot
    
            for d in dirs:
                path = os.path.join(path, d)
                try:
                    self.ftp.mkd(path)
                    debug('Creating directory %s' % path)
                except Exception, e:
                    if str(e).startswith('550'):
                        pass
                    else:
                        warning('Error creating destination: %s, %s' % (path, str(e)))
    
    def transfer_file(self, source):
        self.create_path(source)
        destination = re.sub(self.__staging_path, '', source)

        if self.__docroot != '/':
            destination = self.__docroot + destination

        try:
            with open(source, 'r') as fh:
                info('Moving %s to %s' % (source, destination))
                self.ftp.storbinary('STOR ' + destination, fh)
                debug('Transfer succeeded: %s' % destination)
                return (True, None)
        except Exception, e:
            error('Error transferring file: %s' % source)
            error(str(e))
            return (False, str(e))
    
    def close(self):
        try:
            debug('Closing FTP session.')
            self.is_active = False
            self.ftp.quit()
        except Exception, e:
            warning('Error closing FTP session')
            warning(str(e))
