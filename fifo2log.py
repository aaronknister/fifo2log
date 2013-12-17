#!/usr/bin/env python
import signal
import stat
import os
import argparse
import subprocess
import sys

ROTATELOGS="/usr/sbin/rotatelogs"
VERBOSE=False
CHILDREN_PIDS=[]

class StrToOctal(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    oct_value=int(values,8)
    setattr(namespace, self.dest, oct_value)

def parse_args():
  parser = argparse.ArgumentParser(description='Read logs from a fifo and write to file')
  parser.add_argument('--fifo',type=str,help='path to fifo',required=True)
  parser.add_argument('--logfile',help='Name of logfile',required=True)
  parser.add_argument('-r','--rotatelogs',help='Path to rotatlogs command',default=ROTATELOGS)
  parser.add_argument('-u','--umask',default=0o022,help='umask (default is 022)',action=StrToOctal)
  parser.add_argument('-p','--pid-file',help='path to PID file')
  parser.add_argument('-v','--verbose',help='verbose',action="store_true", default=False)
  rotation_group=parser.add_mutually_exclusive_group(required=True)
  rotation_group.add_argument('--seconds',help='Rotation time in log seconds')
  rotation_group.add_argument('--size',help='Max size of log file prior to rotation')
  return parser.parse_args(sys.argv[1:])

def debug(msg):
  if VERBOSE:
    print "DEBUG: %s" % msg

def is_fifo(file):
  return stat.S_ISFIFO(os.stat(file).st_mode)

def init_fifo(fifo):
  path_dirname=os.path.dirname(fifo)

  if not os.path.exists(path_dirname):
    debug("Fifo path '%s' does not exist, creating" % fifo_path)
    os.makedirs(path_dirname)

  if not os.path.exists(fifo):
    debug("Fifo '%s' doesn't exist" % fifo)
    debug("Creating fifo '%s'" % fifo)
    os.mkfifo(fifo)
  else:
    if not is_fifo(fifo):
      raise Exception,"File '%s' exists but is not a fifo" % fifo

  return open(fifo,'w+')

def init_rotatelogs(rotate_logs,log_file,rotate_arg,fifo_fd_num):
  logfile_dirname=os.path.dirname(log_file)

  if not os.path.exists(logfile_dirname):
    os.makedirs(logfile_dirname)

  return subprocess.Popen([rotate_logs,log_file,rotate_arg],stdin=fifo_fd_num,close_fds=True)

def set_umask(umask):
  orig_umask=os.umask(0)
  debug("Changing umask to %s from %s" % (oct(umask),oct(orig_umask)))
  os.umask(umask)

def signal_handler(signum,frame):
  print "Caught signal %d. Killing children..." % signum
  for pid in CHILDREN_PIDS:
    print "\tKilling child pid %d" % pid
    os.kill(pid,signal.SIGKILL)

  sys.exit(1)

def set_signal_handler():
  for sig in [signal.SIGINT,signal.SIGHUP,signal.SIGQUIT,signal.SIGTERM]:
    signal.signal(sig,signal_handler)

if __name__ == "__main__":
  set_signal_handler()

  args=parse_args()
  VERBOSE=args.verbose

  set_umask(args.umask)
  fifo_f=init_fifo(args.fifo)
  rotate_arg=args.seconds or args.size
  rlogs_p=init_rotatelogs(args.rotatelogs,args.logfile,rotate_arg,fifo_f.fileno())
  CHILDREN_PIDS.append(rlogs_p.pid)
  rlogs_p.wait()
