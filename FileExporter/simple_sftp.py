import logging
import os
import re

from util import die

try:
    import paramiko
except ImportError:
    die("Unable to import paramiko, please ensure that it is installed correctly.")

debug = logging.getLogger('fes').debug
info = logging.getLogger('fes').info
warning = logging.getLogger('fes').warning
error = logging.getLogger('fes').error

class BasicSFTPClient():

    def __init__(self, settings):
        logging.getLogger('paramiko').setLevel(logging.INFO)
        self.__username = settings['USERNAME']
        self.__password = settings['PASSWORD']
        self.__server = settings['FTP_SERVER']
        self.__staging_path = settings['STAGING_PATH']
        self.__port = settings['SSH_PORT']
        if settings['DESTINATION']:
            self.__docroot = settings['DESTINATION']
        else:
            self.__docroot = None
        debug('Creating SFTP session to %s with %s/%s on port %s' % (self.__server, self.__username, self.__password, self.__port))

        self.connect()

    def connect(self):
        # Create SFTP session
        self.transport = paramiko.Transport((self.__server, self.__port))
        self.transport.connect(username=self.__username, password=self.__password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)

    def create_path(self, filename):
        debug('Creating paths if required...')
        if self.__docroot:
            try:
                debug('Creating destination dir: %s' % self.__docroot)
                self.sftp.mkdir(self.__docroot)
            except Exception, e:
                warning('Error creating destination: %s, %s' % (self.__docroot, str(e)))
        if self.__staging_path != os.path.dirname(filename):
            r = re.sub(self.__staging_path, '', os.path.dirname(filename))
            dirs = filter(None, r.split('/'))
            print "DIRS: ", dirs
            if self.__docroot:
                path = self.__docroot
            else:
                path = ""
    
            for d in dirs:
                path = os.path.join(path, d)
                try:
                    self.sftp.mkdir(path)
                    debug('Creating directory %s' % path)
                except Exception, e:
                    warning('Error creating directory: %s, %s' % (path, str(e)))
#                    if str(e).startswith('550'):
#                        pass
#                    else:
#                        warning('Error creating destination: %s, %s' % (path, str(e)))

    def transfer_file(self, source):
        self.create_path(source)

#        debug('doc: %s' % self.__docroot)
#        debug('staging: ' + self.__staging_path)
#        debug('regex: ' + re.sub(self.__staging_path, '', source))

        destination = re.sub(self.__staging_path + '/', '', source)
        if self.__docroot:
            destination = os.path.join(self.__docroot, destination)

#        debug('dest: ' + destination)

        try:
            info('Moving %s to %s' % (source, destination))
            self.sftp.put(source, destination)
            debug('Transfer succeeded: %s' % destination)
            return (True, None)
        except Exception, e:
            try:
                self.transport.close()
            except:
                pass
            error('Error transferring file: %s' % source)
            error(str(e))
            return (False, str(e))

    def close(self):
        try:
            debug('Closing SFTP session.')
            self.transport.close()
        except Exception, e:
            warning('Error closing SFTP session')
            warning(str(e))

