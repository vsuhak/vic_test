# coding=utf-8
"""
  The module contains helper classes

  @copyright: 2010 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: vsu

  @todo: consider rewriting xml stuff using ElementTree
"""

import httplib
import os
import re
import socket
import inspect
import sys
import tempfile
import xmlrpclib
import codecs
import time
import traceback
import shutil
import fnmatch
import gzip
import smtplib
import netifaces
from collections import deque, defaultdict
from datetime import datetime
from ftplib import FTP, Error
from email.MIMEText import MIMEText
from telnetlib import Telnet

import BTE.src.Constants as const
import BTE.src.CustomExceptions as CustomExceptions
from BTE.src.CustomExceptions import BTEResourceCreationError
from BTE.src.LabEnvironment import Environment


def email(to, subject, message):
  """
  Sends an e-mail message.
  @param to: to address or company acronym
  @type to: string
  @param subject: message subject
  @type subject: string
  @param message: message body
  @type message: string
  """
  sender = Environment.get_notifier_email()
  smtp_port = Environment.get_smtp_port()
  smtp_server = Environment.get_smtp_server()

  footer = "\n--------------\n" + \
         "This is an automated message, don't reply.\n"
  msg = MIMEText(message + footer)
  msg['From'] = sender
  msg['To'] = to
  msg['Subject'] = subject

  smtp = smtplib.SMTP(smtp_server, smtp_port)
  smtp.sendmail(sender, [to], msg.as_string())
  smtp.quit()


def uniquify_order(seq):
  """
  Uniquifies a sequence and preservers initial order.
  Not very efficient but good enough for now.
  @param seq: sequence to uniquify
  @type seq: list
  @return: uniquified sequence with preserved order: [3,1,1,4,4] -> [3,1,4]
  @rtype: list
  """
  seen = set()
  unique_seq = []
  for e in seq:
    if e not in seen:
      seen.add(e)
      unique_seq.append(e)
  return unique_seq


def search_list_in_string_exact(strings, string):
  """
  Checks if the string 'string' contains any strings from the list 'strings'.
  It checks for an exact match so 'somestring' will match 'somestring', 'somestring.',
  'somestring(asdasd)' but not 'somestringtoo'.
  @param strings: list of strings to search
  @type strings: list
  @param string: the string we are searching in
  @type string: string
  @return: None or the string that was found
  """
  for s in strings:
    if re.search(r"\b%s\b" % s, string):
      return s
  return None


def get_all_custom_exception_names():
  """
  Returns a list of custom exception names that are defined in BTE.src.CustomExceptions.
  Assumes that only exception classes are defined in that module.
  @return: list of strings
  @rtype: list
  """
  classes = inspect.getmembers(CustomExceptions, inspect.isclass)
  return [name for name, cls in classes if cls.__module__ == CustomExceptions.__name__]


def cleanup_proxy(context):
  """
  A proxy method that is used to call cleanup methods defined outside BTE (for
  example in Common).
  @param context: cleanup method context in the form::
                  context = {const.C_PATH: <path_to_module>,
                             const.C_MODULE: <module.name>,
                             const.C_METHOD: <method_name>,
                             const.C_ARGS: (<args>, <to>, <actual>,
                                            <cleanup>, <method>)}
  """
  sys_path_append(context[const.C_PATH])
  module = __import__(context[const.C_MODULE], fromlist=[context[const.C_METHOD]])
  getattr(module, context[const.C_METHOD])(*context[const.C_ARGS])
  sys.path.pop(sys.path.index(context[const.C_PATH]))


def list_to_string(lst):
  """
  Converts a list of unicode strings to a unicode string representing the list contents.
  Used to keep the logs clean, does clutter output with u-s like str([u'str1', u'str2']) does.
  If the list contains a non-string element (which shouldn't really if this is only used
  to convert STAF messages), the default string representation of the list is returned
  (that uses each element's __repr__).
  @param lst: list of unicode strings
  @return: representation of the list as a string
  @rtype: unicode string
  """
  try:
    return u"[%s]" % (u", ".join(lst))
  except TypeError:
    return str(lst)
lts = list_to_string  # Create an alias


def timestamp():
  """it returns the current timestamp in the format Y-m-d H:M:S.microsec
  for ex. 2011-07-21 08:33:55.580349
  @return:  the current timestamp
  @rtype: datetime
  """
  return datetime.today()


def replace_escaping_symbols(string_to_replace):
  """It replaces symbols which should be escaped with '_'
  for ex. ':' has to be replaced because an os doesn't handle correctly folders, which names contain ':'

  @param string_to_replace: a string to replace
  @type string_to_replace: string
  @return: a string with replaced escaping symbols
  @rtype: string
  """
  symbols_to_replace = [':', '(', ')', ' ']
  symbols_to_replace_to = '_'
  for symbol in symbols_to_replace:
    string_to_replace = str(string_to_replace).replace(symbol, symbols_to_replace_to)
  return string_to_replace


def create_stdout(stdout_filename):
  """it creates a new stdout and stderr for a process
  @param stdout_filename: a name of a file where stdout will be written
  @type stdout_filename: string
  @return: a reference to an original stdout and stderr
  @rtype: stdout, stderr
  """
  print stdout_filename
  if (os.path.exists(stdout_filename)):
    os.remove(stdout_filename)
  sys.stdout.flush()
  sys.stderr.flush()
  stdout_original = sys.stdout
  stderr_original = sys.stderr
  sys.stdout = codecs.open(stdout_filename, "w", "utf-8")
  sys.stderr = codecs.open(_get_stderr_file_name(stdout_filename), "w", "utf-8")
  return stdout_original, stderr_original


def create_ftp_test_run_folder(queue_task_id):
  """it creates a folder on a ftp server
  @param queue_task_id: an id of the task. it is used for creation of a folder on the ftp server
  @type queue_task_id: int
  """
  ftp_log_root = Environment.get_hyperion_ftp_log_root()
  ftp_folder = os.path.join(str(ftp_log_root), str(queue_task_id))
  _ftp_action((ftp_folder,))


def upload_logs(source, queue_task_id, desitation_folder="", recursive=True):
  """it uploads all log files to the Hyperion's web site
  the following command will be used
  scp -r mydir someuser@hyperion.bang-olufsen.dk:/tmp
  @param source: a source (a file or a folder) to upload
  @type source: string
  @param queue_task_id: an id of the task. it is used for creation of a folder on the ftp server
  @type queue_task_id: int
  @param desitation_folder: a full name of the destination folder starting from the ftp_log_root.
                if it is "", logs will be uploaded to the ftp_log_root
  @type desitation_folder: string
  @param recursive: wheather a source should be uploaded recursivly
  @type recursive: boolean
  """
  # check sources
  if not (source is not None and os.path.exists(source)):
    print "Logs were not uploaded. The path '%s' does not exist" % source
    return False

  # define parameter
  ftp_log_root = Environment.get_hyperion_ftp_log_root()
  ftp_folder = os.path.join(str(ftp_log_root), str(queue_task_id), desitation_folder)

  spec_symbols = [" ", "(", ")"]
  if os.path.isdir(source):
    # pylint:disable=W0612
    for root, _dirs, files in os.walk(source):
      if (not recursive and root != source):
        break

      remote_path = root.replace(source, ftp_folder)

      # replace special symbols
      for symbol in spec_symbols:
        remote_path = remote_path.replace(symbol, "\\" + symbol)

      _ftp_action((remote_path,))
      for f in files:
        _ftp_action((os.path.join(root, f), os.path.join(remote_path, f)))
  else:
    _ftp_action((ftp_folder,))
    _ftp_action((source, os.path.join(ftp_folder, os.path.basename(source))))


def upload_stdout(stdout_filename, stdout_original, stderr_original, log_folder):
  """it merges stdout and stderr into the one stdout file
  and uploads it into the testcase log folder
  @param stdout_filename: a name of a file where stdout will be written
  @type stdout_filename: string
  @param stdout_original: a reference to an original stdout
  @type stdout_original: stdout
  @param stderr_original: a reference to an original stderr
  @type stderr_original: stderr
  @param log_folder: a folder to upload results
  @type log_folder: string
  @todo: if a log_folder is None, upload stdout files to a folder of a test suite
  """
  sys.stdout.flush()
  sys.stderr.flush()
  sys.stdout.close()
  sys.stderr.close()
  sys.stdout = stdout_original
  sys.stderr = stderr_original

  stderr_filename = _get_stderr_file_name(stdout_filename)

  if (os.path.exists(stdout_filename) and os.path.exists(stderr_filename)):
    f_stderr = open(stderr_filename, "r")
    err_lines = f_stderr.readlines()

    if err_lines:
      f_stdout = open(stdout_filename, "a")
      f_stdout.write("\nSTDERR output:\n")
      f_stdout.writelines(err_lines)
      f_stdout.close()
    f_stderr.close()
    os.remove(stderr_filename)

  if (os.path.exists(stdout_filename) and log_folder is not None):
    shutil.move(stdout_filename, log_folder)


def compress_files(file_extension, search_folder):
  """it compresses and removes files with the extension in the list from the search_folder and sub directories.
  @param file_extension: A list of file extensions that should be compressed.
  @type file_extension: list
  @param search_folder: The base directory where the search should take place.
  @type search_folder: string
  """
  # run through all extensions
  # check sources
  if not (search_folder is not None and os.path.exists(search_folder)):
    print "Logs were not compressed. The path '%s' does not exist" % search_folder
    return

  for file_type in file_extension:
    # pylint:  disable=W0612
    for root, _dirs, filenames in os.walk(search_folder):
      for filename in fnmatch.filter(filenames, "*.%s" % file_type):
        full_filename = os.path.join(root, filename)
        with open(full_filename, "rb") as f_in:
          f_out = gzip.open("%s.gz" % full_filename, "wb")
          f_out.writelines(f_in)
          f_out.close()
        os.remove(full_filename)


def sys_path_append(path):
  """ it appends a path to the sys path if it is not already there
  @param path: a path to append
  @type path: string
  """
  if path not in sys.path:
    sys.path.append(path)


def _get_stderr_file_name(stdout_filename):
  """it calculates name for stderr output based on the stdout's filename
  @param stdout_filename: std_out filename
  @type stdout_filename: string
  @return: a name of a file where stderr will be written
  @rtype: string
  """
  basename = os.path.basename(stdout_filename)
  stderr_filename = "tmp_err_" + basename
  return os.path.join(os.path.dirname(stdout_filename), stderr_filename)


def _ftp_action(args):
  """it uploads a file or create a folder using the ftp connection, depending on arguments
  @param args: a typil of arguments,
              if a len of the typil is 1 ("folder",) the folder will be created,
              if a len of the typil is 2 ("local_file","remote_file") the local file will be uploaded
  @type args: typil
  """
  # 5 min to upload files
  connection_timeout = 300
  if len(args) == 1:
    # only 60s to create a folder
    connection_timeout = 60
  ftp_server = Environment.get_hyperion_ftp_host()
  ftp_user, ftp_password = Environment.get_hyperion_ftp_username_password()

  # trying to connect 5 times to upload a log
  counter = 0
  max_count_attempts = 5
  while (counter < max_count_attempts):
    ftp_srv = None
    try:
      ftp_srv = FTP(ftp_server, ftp_user, ftp_password, timeout=connection_timeout)
      break
    # pylint: disable=W0703
    except Error as e:
      print "%s: An exception '%s' happened during creation of a ftp conneciton. Attempt %s" % (timestamp(), e, counter)
      print "".join(traceback.format_exception(*sys.exc_info()))
      sys.exc_clear()
      if ftp_srv is not None:
        try:
          ftp_srv.quit()
        # pylint: disable=W0703
        except Error as e_quit:
          print "%s: An exception '%s' happened during closing a ftp conneciton" % (timestamp(), e_quit)
          ftp_srv.close()

    counter += 1
    time.sleep(counter)

  ftp_log_root = Environment.get_hyperion_ftp_log_root()
  if(counter >= max_count_attempts):
    print "%s: Cannot connect to the ftp server in %s attempts" % (timestamp(), max_count_attempts)
    return
  try:
    if len(args) == 1:
      folder, = args

      # creating folders recursivly
      folders_str = folder.replace(ftp_log_root, "").strip('/')
      folders = folders_str.split('/')
      path = ftp_log_root
      for fold in folders:
        path = os.path.join(path, fold)
        if path not in ftp_srv.nlst(os.path.dirname(path)):
          ftp_srv.mkd(path)
          # drwxr-xr-x
          ftp_srv.voidcmd('SITE CHMOD 775 %s' % path)

    # uploading a file
    elif len(args) == 2:
      source, dest = args
      if (os.path.exists(source)):
        # if destination exits, change the name
        if dest in ftp_srv.nlst(os.path.dirname(dest)):
          dest = dest + "." + time.strftime("%Y_%m_%d_%H_%M_%S")

        ftp_srv.storbinary("STOR %s" % dest, open(source, "rb"))
        # -rw-r--r--
        ftp_srv.voidcmd('SITE CHMOD 644 %s' % dest)
      else:
        print "%s: cannot upload. the source doesn't exist: '%s'" % (timestamp(), source)
    else:
      print "%s: Incorrect arguments: '%s'" % (timestamp(), str(args))
  # pylint: disable=W0703
  except Error as e:
    print "%s: An exception '%s' happened during creation of a folder or uploading of a file" % (timestamp(), e)
    print "".join(traceback.format_exception(*sys.exc_info()))
    sys.exc_clear()
  finally:
    try:
      ftp_srv.quit()
    # pylint: disable=W0703
    except Error as e_quit:
      print "%s: An exception '%s' happened during closing a ftp conneciton" % (timestamp(), e_quit)
      ftp_srv.close()


def analyze_sys_log(log_file_name, test_hash, test_results, keywords, role_name=None):
  """it analyses a log file and adds (annotate) results into test_results
  @param log_file_name: a full name of the log file
  @type log_file_name: string
  @param test_hash: a unique indentificator of a test which was printed in a log
  @type test_hash: string
  @param test_results: a result of execution of a test case
  @type test_results: BeoTestResult
  @param keywords: list of words to search
  @type keywords: list
  @param role_name: a name of the role (None by default),
                    if there are more then one DUT in the test.
  @type role_name: string
  @return: whether a log file has been analysed
  @rtype: boolean
  """
  if not os.path.exists(log_file_name):
    print "the file with the name '%s' does not exists" % log_file_name
    return False

  if len(keywords) == 0:
    print "there are no key words for analysis"
    return False

  is_test_hash_found = False
  is_analysed = False
  kw_dict, _keywords = test_results.GetAnnotations().get(const.message_type_syslog, (defaultdict(list), None))
  kw_dict = defaultdict(list, kw_dict)

  with open(log_file_name, 'r') as log_file:
    for i, line in enumerate(log_file):
      if not is_test_hash_found:
        is_test_hash_found = str(test_hash) in line
        continue
      is_analysed = True
      for keyword in keywords:
        key = keyword
        if role_name != None:
          key = "%s_%s" % (role_name, keyword)
        if keyword in line:
          kw_dict[key].append("(%s): %s" % (i + 1, line))
    test_results.Annotate({const.message_type_syslog: (dict(kw_dict), dict(kw_dict).keys())})
  return is_analysed


def is_host_alive(host, port=None):
  """it checks whether a host is alive by connecting using Telnet
  Telnet is also necessary when a board behind a router.

  if a message of the exception is "Connection refused",
  it means that the host is alive, but telnet is not running on the port 'port'

  @param port: a port Telnet should connect to, default is None
  @type port: integer
  @return: result of check
  @rtype: boolean
  """
  CONNECTION_REFUSED = "Connection refused"
  telnet = Telnet()
  try:
    timeout_sec = 3
    print "is_host_alive: trying to connect by Telnet, host=%s, port=%s, timeout_sec=%s" % (host, port, timeout_sec)
    telnet.open(host, port, timeout_sec)
    telnet.close()
    return True
  except socket.error as exc:
    print exc
    if CONNECTION_REFUSED in str(exc):
      return True
    return False


class SocketHelper (object):
  """a class containing helper functions"""

  @staticmethod
  def get_local_net_ip_address():
    """Returns the ip address of the first found network interface
    excluding ones from the excluded list
    @return: string containing local machine's ip address
    @rtype: string
    """
    # pylint: disable = no-member
    excluded_network_interfaces = ["lo"]
    network_interfaces = netifaces.interfaces()
    network_interfaces = list(set(network_interfaces).difference(excluded_network_interfaces))
    print("all network interfaces filtered: %s" % network_interfaces)

    for interface in network_interfaces:
      ip_address = SocketHelper.get_ip_address(interface)
      if ip_address:
        return ip_address
    raise BTEResourceCreationError("Could not get local net ip.")

  @staticmethod
  def get_ip_address_local():
    """get local ip address: 127.0.0.1
    @return: local IP address
    @rtype: string"""
    return SocketHelper.get_ip_address("lo")

  @staticmethod
  def get_ip_address(ifname):
    """get IP address of the a pc by a network device
    @param ifname: name of the network device such as: lo, eth0 etc.
    @type ifname: string
    @return: ip address of the network interface
    @rtype: string or None, if not found
    """
    # pylint: disable = no-member
    ip_addresses = netifaces.ifaddresses(ifname)
    # {17: [{'peer': '00:00:00:00:00:00', 'addr': '00:00:00:00:00:00'}],
    # 2: [{'peer': '127.0.0.1', 'netmask': '255.0.0.0', 'addr': '127.0.0.1'}],
    # 10: [{'netmask': 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'addr': '::1'}]}
    print("ip addresses for the interface %s: %s" % (ifname, ip_addresses))
    ip_address = ip_addresses.get(netifaces.AF_INET, None)
    if ip_address:
      return ip_address[0].get("addr", None)
    return None


class SerializableQueue(object):
  """ the class implements a queue which could be serialized to a file and loaded back
  if there is more than n items in a queue, it is serialized into a file and becomes empty.
  Only strings can be serialized. Every item in the queue is saved as a separated string in a serialization file
  @todo: make the type check for the requirement, that "Only strings can be serialized"

  @ivar __queue: a queue to store queries
  @type __queue: deque
  @ivar __full_file_name: a full name of the file for serialization
  @type __full_file_name: string
  @ivar __max_length: max length of the queue until serialization happens
  @type __max_length: int
  @ivar __is_queue_serialized: a flag, indicating the the queue has been serialized
  @type __is_queue_serialized: boolean
  """
  def __init__(self, full_file_name, max_length):
    self.__queue = deque()
    if full_file_name is None:
      self.__full_file_name = tempfile.mktemp()
    else:
      self.__full_file_name = full_file_name
    self.__max_length = max_length
    self.__is_queue_serialized = False

  def __del__(self):
    if os.path.exists(self.__full_file_name) and os.path.getsize(self.__full_file_name) == 0:
      os.remove(self.__full_file_name)

  def __save(self):
    """ it saves a queue as strings into a file
    """
    open_mode = "a"
    if not self.__is_queue_serialized:
      open_mode = "w"
    with open(self.__full_file_name, open_mode) as f:
      for item in self.__queue:
        f.write("%s%s" % (item, "\n"))

  def __load(self, queue):
    """it loads the serialized queue from the file into a temporary queue
    @param queue: a queue to load date into
    @type queue: deque
    @return: a queue with loaded results
    @rtype: deque
    """
    with open(self.__full_file_name, "r") as f:
      for ln in f:
        queue.append(ln.rstrip("\n"))
    return queue

  def get_queue(self):
    """It returns the queue
    @return: a queue with results
    @rtype: deque
    """
    queue = []
    if self.__is_queue_serialized:
      queue = self.__load(queue)
    queue.extend(self.__queue)
    return queue

  def append(self, obj):
    """append an obj to the right end of the queue
    if there is more than n items in a queue, it is serialized into a file and becomes empty.
    @param obj: an object to be appended
    """
    self.__queue.append(obj)
    if len(self.__queue) > self.__max_length:
      self.flush()

  def extend(self, objs):
    """It extend a queue with another iterable object
    if there is more than n items in a queue, it is serialized into a file and becomes empty.
    @param objs: an iterable list of objects
    """
    self.__queue.extend(objs)
    if len(self.__queue) > self.__max_length:
      self.flush()

  def flush(self):
    """it flushes the queue into the file
    """
    self.__save()
    self.__queue.clear()
    self.__is_queue_serialized = True

  def clear(self):
    """it clear the queue
    """
    self.__queue.clear()
    self.__is_queue_serialized = False


class TimeoutServerProxy(xmlrpclib.ServerProxy):
  """a xmlrpc servert proxy which uses a timeout for connections
  """
  def __init__(self, uri, timeout=5, *l, **kw):
    kw['transport'] = TimeoutTransport(timeout=timeout, use_datetime=kw.get('use_datetime', 0))
    xmlrpclib.ServerProxy.__init__(self, uri, *l, **kw)


class TimeoutTransport(xmlrpclib.Transport):
  """ a timeout transport
  @ivar timeout: a timeout in sec for a socket
  @type timeout: int
  """
  def __init__(self, timeout=10, *l, **kw):
    # for compatibility with 2.7
    self._connection = (None, None)
    self._extra_headers = []

    xmlrpclib.Transport.__init__(self, *l, **kw)

    self.timeout = timeout

    if sys.version.startswith("2.6"):
      self.make_connection = self.make_connection_26
    elif sys.version.startswith("2.7"):
      self.make_connection = self.make_connection_27

  def make_connection_26(self, host, port=None):
    conn = TimeoutHTTP(host, port)
    conn.set_timeout(self.timeout)
    return conn

  def make_connection_27(self, host, port=None):
    if self._connection and host == self._connection[0]:
      return self._connection[1]

    # pylint: disable=W0612
    chost, self._extra_headers, _x509 = self.get_host_info(host)
    self._connection = host, httplib.HTTPConnection(chost, timeout=self.timeout, port=port)
    return self._connection[1]


class TimeoutHTTP(httplib.HTTP):
  def set_timeout(self, timeout):
    self._conn.timeout = timeout


# commnenting WatchDog, but keeping it for the future.
# It is possible that it will be needed
# class WatchDog(object):
#   """the class to set an alarm then rasing an exception
#   @raise TestTimeout: the exception is raised, when timeout happenes
#   """
#   def __init__(self, timeout, timeout_msg, execute_counter=1):
#     """constructor
#     @param timeout: a timeout to wait
#     @type timeout: integer
#     @param timeout_msg: a message to print out in exception, when the timeout happenes
#     @type timeout_msg: string
#     @param execute_counter: how many times the watchdog should be executed, default value is 1
#     @type execute_counter: integer
#     """
#     self._timeout = timeout
#     self._timeout_msg = timeout_msg
#     self._execute_counter = execute_counter
#
#   def start(self):
#     """starts the ararm
#     """
#     self._execute_counter -= 1
#     signal.signal(signal.SIGALRM, self._raiseTimeout)
#     signal.alarm(self._timeout)
#
#   def stop(self):
#     """it stops the watchdog
#     """
#     signal.alarm(0)
#
#   def _raiseTimeout(self, number, frame):
#     """It raises an exception TestTimeout
#     """
#     if self._execute_counter > 0:
#       self.start()
#     print "*** raising the TestTimeout exception"
#     raise TestTimeout(self._timeout_msg)

from unittest import TestCase
from BTE.unittests.stubs.stubs import BeoTestResultStub


class TimeoutTransportTest(TestCase):

  version_26 = "2.6.3"
  version_27 = "2.7.3"
  timeout_default = 10

  # a PC where the default http port (80) is opened
  host = "hyperion.bang-olufsen.dk"

  def setUp(self):
    """setup"""

  def tearDown(self):
    """teardown"""

  def test_init_timeout_default(self):
    tt = TimeoutTransport(use_datetime=0)
    self.assertEqual(tt.timeout, self.timeout_default, "actual timeout '%s' is not equal with the expected '%s'" % (tt.timeout, self.timeout_default))

  def test_init_timeout_0(self):
    tt = TimeoutTransport(timeout=0, use_datetime=0)
    self.assertEqual(tt.timeout, 0, "actual timeout '%s' is not equal with the expected '%s'" % (tt.timeout, self.timeout_default))

  def test_make_connection_26(self):
    sys.version = self.version_26
    tt = TimeoutTransport(use_datetime=0)
    connection = tt.make_connection(self.host)
    self.assertTrue(isinstance(connection, TimeoutHTTP), "the connection '%s' is not an instance of 'TimeoutHTTP'" % connection)

  def test_make_connection_26_timeout_default(self):
    sys.version = self.version_26
    tt = TimeoutTransport(use_datetime=0)
    connection = tt.make_connection(self.host)
    # pylint: disable=W0212
    connection._conn.connect()
    self.assertEqual(connection._conn.timeout, self.timeout_default,
                     "actual timeout '%s' is not equal with the expected '%s'" % (connection._conn.timeout, self.timeout_default))
    self.assertEqual(connection._conn.sock.gettimeout(), self.timeout_default,
                     "actual timeout for the socket '%s' is not equal with the expected '%s'" % (connection._conn.sock.gettimeout(), self.timeout_default))
    connection._conn.close()

  def test_make_connection_27(self):
    sys.version = self.version_27
    tt = TimeoutTransport(use_datetime=0)
    connection = tt.make_connection(self.host)
    self.assertTrue(isinstance(connection, httplib.HTTPConnection), "the connection '%s' is not an instance of 'httplib.HTTPConnection'" % connection)

  def test_make_connection_27_timeout_default(self):
    sys.version = self.version_27
    tt = TimeoutTransport(use_datetime=0)
    connection = tt.make_connection(self.host)
    connection.connect()
    # pylint: disable=E1103
    self.assertEqual(connection.timeout, self.timeout_default, "actual timeout '%s' is not equal with the expected '%s'" % (connection.timeout, self.timeout_default))
    self.assertEqual(connection.sock.gettimeout(), self.timeout_default,
                     "actual timeout for the socket '%s' is not equal with the expected '%s'" % (connection.sock.gettimeout(), self.timeout_default))
    connection.close()


class SerializableQueueTest(TestCase):
  """the class with tests for the class SerializableQueue
  """
  test_str1 = "string1"
  test_str2 = "string2"
  test_str3 = "string3"
  test_str4 = "string4"
  test_str5 = "string5"
  test_str6 = "string6"
  max_length = 2

  def setUp(self):
    """setup"""
    self.file_full_name = tempfile.mktemp()
#    self.file_full_name = "/home/vsu/tmp/queue.txt"
    self.queue = SerializableQueue(self.file_full_name, self.max_length)

  def tearDown(self):
    """teardown"""
    del self.queue
    if os.path.exists(self.file_full_name):
      os.remove(self.file_full_name)

  def __append(self, expected_res):
    """it appends some objects into the queue and verify the result
    @param expected_res: an expected result
    @type expected_res: string
    """
    for res in expected_res:
      self.queue.append(res)
    actual_res = self.queue.get_queue()
    self.assertEqual(expected_res, actual_res,
                     "expected queue '%s' is not equal to the actual '%s'" % (expected_res, actual_res))

  def __extend(self, expected_res):
    """it extend the queue with some objects and verify the result
    @param expected_res: an expected result
    @type expected_res: list of string
    """
    self.queue.extend(expected_res)
    actual_res = self.queue.get_queue()
    self.assertEqual(expected_res, actual_res,
                     "expected queue '%s' is not equal to the actual '%s'" % (expected_res, actual_res))

  def test__del(self):
    self.queue.flush()
    assert os.path.getsize(self.file_full_name) == 0

    self.queue.__del__()
    self.assertFalse(os.path.exists(self.file_full_name))

  def test_append_empty(self):
    expected_res = []
    self.__append(expected_res)
    self.assertFalse(os.path.exists(self.file_full_name), "the queue file '%s' exists" % self.file_full_name)

  def test_append_1(self):
    expected_res = [self.test_str1]
    assert len(expected_res) == 1, "incorrect length of expected results"
    self.__append(expected_res)
    self.assertFalse(os.path.exists(self.file_full_name), "the queue file '%s' exists" % self.file_full_name)

  def test_append_less_max_length(self):
    expected_res = [self.test_str1, self.test_str2]
    assert len(expected_res) == self.max_length, "incorrect length of expected results"
    self.__append(expected_res)
    self.assertFalse(os.path.exists(self.file_full_name), "the queue file '%s' exists" % self.file_full_name)

  def test_append_more_max_length(self):
    expected_res = [self.test_str1, self.test_str2, self.test_str3]
    assert len(expected_res) == self.max_length + 1, "incorrect length of expected results"
    self.__append(expected_res)
    self.assertTrue(os.path.exists(self.file_full_name), "the queue file '%s' doesn't exists" % self.file_full_name)

  def test_append_more_2max_length(self):
    expected_res = [self.test_str1, self.test_str2, self.test_str3, self.test_str4, self.test_str5, self.test_str6]
    assert len(expected_res) == (self.max_length + 1) * 2, "incorrect length of expected results"
    self.__append(expected_res)
    self.assertTrue(os.path.exists(self.file_full_name), "the queue file '%s' doesn't exists" % self.file_full_name)

  def test_flush(self):
    expected_res = [self.test_str1]
    for res in expected_res:
      self.queue.append(res)
    self.assertFalse(os.path.exists(self.file_full_name))
    self.queue.flush()
    actual_res = self.queue.get_queue()
    self.assertEqual(expected_res, actual_res,
                     "expected queue '%s' is not equal to the actual '%s'" % (expected_res, actual_res))

    self.assertTrue(os.path.exists(self.file_full_name), "the queue file '%s' doesn't exists" % self.file_full_name)

  def test_flush_empty(self):
    self.assertFalse(os.path.exists(self.file_full_name))
    self.queue.flush()
    self.assertTrue(os.path.exists(self.file_full_name), "the queue file '%s' doesn't exists" % self.file_full_name)

  def test_clear(self):
    lst = [self.test_str1]
    for res in lst:
      self.queue.append(res)
    self.queue.clear()
    actual_res = self.queue.get_queue()
    self.assertEqual(len(actual_res), 0,
                     "the actual results '%s' is not empty" % (actual_res))
    self.assertFalse(os.path.exists(self.file_full_name), "the queue file '%s' exists" % self.file_full_name)

  def test_extend_less_max_length(self):
    expected_res = [self.test_str1, self.test_str2]
    assert len(expected_res) == self.max_length, "incorrect length of expected results"
    self.__extend(expected_res)
    self.assertFalse(os.path.exists(self.file_full_name), "the queue file '%s' exists" % self.file_full_name)

  def test_extend_more_max_length(self):
    expected_res = [self.test_str1, self.test_str2, self.test_str3]
    assert len(expected_res) == self.max_length + 1, "incorrect length of expected results"
    self.__extend(expected_res)
    self.assertTrue(os.path.exists(self.file_full_name), "the queue file '%s' doesn't exists" % self.file_full_name)


class AnalyseSysLogTest(TestCase):
  """the class with tests for analyse syslogs
  """
  # def analyze_sys_log(log_file_name, test_hash, test_results, keywords, role_name=None):

  def setUp(self):
    """setup"""
    self.maxDiff = None
    self.data_path = os.path.join(os.path.dirname(__file__), '..', "unittests", "data")
    self.file_name = os.path.join(self.data_path, "syslog.txt")
    self.file_name_empty = os.path.join(self.data_path, "syslog_empty.txt")
    self.file_name_unicode = os.path.join(self.data_path, "syslog_unicode.txt")
    self.hash = "Sink graph connected"
    self.keywords = ["WARN"]
    self.test_result = BeoTestResultStub()
    self.test_result.clear_annotations()

  def tearDown(self):
    """teardown"""
    self.test_result.clear_annotations()

  def test_path_not_exists(self):
    file_name = os.path.join(self.data_path, "not_exists.txt")
    self.assertFalse(analyze_sys_log(file_name, "222", self.test_result, ["1"]))
    self.assertDictEqual(self.test_result.GetAnnotations(), {})

  def test_no_keywords(self):
    self.assertFalse(analyze_sys_log(self.file_name, "222", self.test_result, []))
    self.assertDictEqual(self.test_result.GetAnnotations(), {})

  def test_no_test_hash(self):
    self.assertFalse(analyze_sys_log(self.file_name, "23625347333", self.test_result, self.keywords))
    self.assertDictEqual(self.test_result.GetAnnotations(), {const.message_type_syslog: ({}, [])})

  def test_no_role_name(self):
    self.assertTrue(analyze_sys_log(self.file_name, self.hash, self.test_result, self.keywords))
    expected_res = {'syslog': ({'WARN': ['(14): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:59:fps_sink_graph_playing: Setting sink graph to playing state\n',
                       '(15): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 3\n',
                       '(18): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 4']},
             ['WARN'])}
    self.assertDictEqual(self.test_result.GetAnnotations(), expected_res)

  def test_one_role_name(self):
    self.assertTrue(analyze_sys_log(self.file_name, self.hash, self.test_result, self.keywords, "a3"))
    expected_res = {'syslog': ({'a3_WARN': ['(14): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:59:fps_sink_graph_playing: Setting sink graph to playing state\n',
                       '(15): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 3\n',
                       '(18): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 4']},
             ['a3_WARN'])}
    self.assertDictEqual(self.test_result.GetAnnotations(), expected_res)

  def test_syslog_0_keywords_found(self):
    self.assertTrue(analyze_sys_log(self.file_name, self.hash, self.test_result, ["WRN"]))
    self.assertDictEqual(self.test_result.GetAnnotations(), {const.message_type_syslog: ({}, [])})

  def test_syslog_empty(self):
    self.assertFalse(analyze_sys_log(self.file_name_empty, self.hash, self.test_result, self.keywords))
    self.assertDictEqual(self.test_result.GetAnnotations(), {const.message_type_syslog: ({}, [])})

  def test_syslog_unicode(self):
    self.assertTrue(analyze_sys_log(self.file_name_unicode, self.hash, self.test_result, self.keywords))
    expected_res = {'syslog': ({'WARN': ['(14): Oct 14 16:20:38 (none) fpsd: WARN    GST: 测试測試 fpsd_sink_graph.c:59:fps_sink_graph_playing: Setting sink graph to playing state\n',
                       '(15): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 3\n',
                       '(18): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 4']},
             ['WARN'])}
    self.assertDictEqual(self.test_result.GetAnnotations(), expected_res)

  def test_ananlyse_second_time_dict_not_empty(self):
    self.assertTrue(analyze_sys_log(self.file_name, self.hash, self.test_result, ["59"], "a3"))
    self.assertTrue(analyze_sys_log(self.file_name, self.hash, self.test_result, ["193"], "a4"))
    expected_res = {'syslog': ({'a3_59': ['(14): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:59:fps_sink_graph_playing: Setting sink graph to playing state\n'],
              'a4_193': ['(15): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 3\n',
                         '(18): Oct 14 16:20:38 (none) fpsd: WARN    GST: fpsd fpsd_sink_graph.c:193:bus_call: Changed sink to state 4']},
             ['a4_193', 'a3_59'])}

    self.assertDictEqual(self.test_result.GetAnnotations(), expected_res)

# commnenting WatchDog, but keeping it for the future.
# It is possible that it will be needed
# class WatchDogTest(TestCase):
#   """testing watchdog
#   """
#   def setUp(self):
#     """setup"""
#     self.tst_timeout = 4
#     self.wd_timeout = 0
#
#   def tearDown(self):
#     """teardown"""
#
#   def test_timeout(self):
#     self.wd_timeout = 3
#     self.assertRaises(TestTimeout, self._wd_start, *(self.wd_timeout, 1))
#
#   def test_timeout_twice_stop(self):
#     self.wd_timeout = 2
#     wd = WatchDog(self.wd_timeout, "the exception happened", 2)
#     wd.start()
#     self.assertRaises(TestTimeout, self._wd_start_simple, *(self.wd_timeout,))
#     wd.stop()
#     time.sleep(self.tst_timeout)
#
#   def test_timeout_twice(self):
#     self.wd_timeout = 2
#     wd = WatchDog(self.wd_timeout, "the exception happened", 2)
#     wd.start()
#     self.assertRaises(TestTimeout, self._wd_start_simple, *(self.wd_timeout,))
#     self.assertRaises(TestTimeout, self._wd_start_simple, *(self.wd_timeout,))
#     wd.stop()
#     time.sleep(self.tst_timeout)
#
#   def test_no_timeout(self):
#     self.wd_timeout = 6
#     self.assertEqual(0, self._wd_start(self.wd_timeout, 1))
#
#   def _wd_start(self, timeout, counter):
#     wd = WatchDog(timeout, "the exception happened", counter)
#     wd.start()
#     time.sleep(self.tst_timeout)
#     wd.stop()
#     time.sleep(self.tst_timeout)
#     return 0
#
#   def _wd_start_simple(self, timeout):
#     time.sleep(self.tst_timeout)
#     return 0


# if __name__ == "__main__":
 # integration tests
  # print SocketHelper.get_ip_address("eth1")
#   print SocketHelper.get_ip_address_local()
#   print SocketHelper.get_local_net_ip_address()
#   print timestamp()

  # unittests
#   import unittest
#   test_sutie = unittest.TestLoader().loadTestsFromTestCase(SerializableQueueTest)
#   test_sutie.addTests(unittest.TestLoader().loadTestsFromTestCase(TimeoutTransportTest))
#   test_sutie.addTests(unittest.TestLoader().loadTestsFromTestCase(AnalyseSysLogTest))
#   test_sutie.addTests(unittest.TestLoader().loadTestsFromTestCase(WatchDogTest))
#   unittest.TextTestRunner(verbosity=2).run(test_sutie)

#   test = SerializableQueueTest("test_append_less_max_length")
#   test = TimeoutServerProxyTest("test_append_less_max_length")
#   test = AnalyseSysLogTest("test_no_keywords")
#   test = WatchDogTest("test_no_timeout")
#  test = WatchDogTest("test_timeout")
#  test = WatchDogTest("test_timeout_twice")
#  test = WatchDogTest("test_timeout")
#  unittest.TextTestRunner().run(test)
