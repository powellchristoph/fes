#!/usr/bin/python

"""
File Export Service

Scans the configured STAGING_PATH and moves appropriate files to the
EXPORT_PATH. It can also push files out via FTP, if configured.

"""

__author__ = 'Chris Powell'

import os
import sys

import getopt
import logging
import traceback

from FileExporter.util import die, setup_logging, read_config
from FileExporter.lockfile import LockFile
from FileExporter.version import VERSION
from FileExporter.file_exporter import FileExporter

info = logging.getLogger('fes').info

def usage():
    print "Usage:"
    print "%s [-c configfile | --config=configfile] [-h | --help] --daemon --debug --version" % sys.argv[0]
    print
    print
    print " --config:       The name of the config file to parse"
    print " --daemon:       Run FES in daemon mode"
    print " --debug:        Enables debug logging"
    print " --version:      Prints the version of FES and exits"
    print " --test:         Tests that the service has the appropriate permisssions"
    print " --help:         Print the usage"

def test_status():
    import shutil
    settings = read_config(config_file)
    for path in ['STAGING_PATH', 'EXPORT_PATH']:
        try:
            tmp_file = os.path.join(settings[path], 'tmp_file')
            tmp_dir = os.path.join(settings[path], 'tmp_dir')
            with open(tmp_file, 'w') as fh:
                data = os.urandom(1024)
                fh.write(data)
            os.mkdir(tmp_dir)
            shutil.move(tmp_file, tmp_dir)
            shutil.rmtree(tmp_dir)
            print '%s tested ok!\n' % path
        except Exception, e:
            print 'Somthing went wrong. Double check the file permissions on the %s' % path
            print 'The FES will not run as it stands, please resolve the issue.\n'
            print str(e)

    if settings['MOVE_TYPE'] == 'ftp_push':
        from FileExporter.simple_ftp import BasicFTPClient
        print 'FTP export configured, testing now...'
        tmp_file = os.path.join(settings[path], 'tmp_file')
        with open(tmp_file, 'w') as fh:
            fh.write(os.urandom(1024))

        try:
            ftp = BasicFTPClient(settings)
        except Exception, e:
            die('Unable to connect to FTP server', str(e))

        (success, errmsg) = ftp.transfer_file(tmp_file, 'delete.me')
        if not success:
            die('Transfer to server failed!!', errmsg)
        ftp.close()

        print 'FTP test ok!'

if __name__ == '__main__':
    config_file = '/opt/fes/fes.conf'
    daemon = 0
    enable_debug = 0
    args = sys.argv[1:]
    try:
        (opts, getopts) = getopt.getopt(args, 'c:h?',
                ['config=', 'version', 'daemon', 'debug', 'test', 'help'])

    except:
        print '\nInvalid command line option detected.'
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-h', '-?', '--help'):
            usage()
            sys.exit(0)
        if opt in ('-c', '--config'):
            config_file = arg
        if opt == '--daemon':
            daemon = 1
        if opt == '--debug':
            enable_debug = 1
        if opt == '--version':
            print "FES version:", VERSION
            sys.exit(0)
        if opt == '--test':
            print 'Starting test now...\n'
            test_status()
            sys.exit(0)

    settings = read_config(config_file)

    setup_logging(settings, enable_debug, daemon)

    lock_file = LockFile(settings['LOCK_FILE'])

    lock_file.create()

    try:
        fe = FileExporter(settings, lock_file, daemon)
    except Exception, e:
        traceback.print_exc(file=sys.stdout)
        print "\nFES exited abnormally"

    # Remove lock file on exit
    lock_file.remove()
