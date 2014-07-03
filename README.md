File Export Service
===================

The File Export Service is a simple service that moves files. It is intentded to assist in use cases where you need to recieve a file but control when it is available on the receiving side.

In our case, we used Aspera to receive files on a server and then make that file accessible once its finished transferring and not have another process or person interfere with it. It also can export the files to a downstream file or ftp server.

You can configure the following *MOVE_TYPE*:
* pull - This simply moves the file from *STAGING_PATH* to *EXPORT_PATH*. The export can be a local file system path or a network mount to facilitate a transfer to another server easily.
* ftp_push - This will deliver the files to the configured remote server via FTP.
* sftp_push - This will deliver the files to a remote server via SFTP.

If you use the ftp_push/sftp_push, ensure that you have the proper credentials inputed. A username/password and server are required.

EXCLUDES can also be configured to ignore certain files based on REGEX pattern. These are configured in the fes.conf. The included ones are set to ignore working, partial and checkpoint files from Aspera or Signiant transfers. The REGEX must be python style.

EXCLUDES = "^#work_file#","^#chkpt_file#","\.partial$","\.aspx$"

An optional *DESTINATION* may be set, in which case all files will be placed into a created directory of that name.

*SLEEP_INTERVAL* is the interval in which FES checks for new files in the *STAGING_PATH*. The default is 5 minutes.

*DAEMON_LOG* is the log file which the FES process writes too.

The *NAGIOS_ALERT* setting will create a file called alert.txt containing any possible errors. There would then be a Nagios check which tested for the existence of the file and parse any errors.

* README.md - The readme.
* fes - Redhat/Centos style init script.
* fes.conf - config file for FES.
* fes.logrotate - Logrotate config file, move to /etc/logrotate.d/fes
* fes.py - Main process file
* fes.spec - RPM spec file
