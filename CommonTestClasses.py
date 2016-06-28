# coding=utf-8
"""
  The module contains test cases' base classes and classes, which are necessary for execution of test cases.

  @copyright: 2010-2013 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: vsu

  new changes in for the branch
"""

import logging
import traceback
import sys
import os
import time
import tempfile
import shutil
import types
import json
from unittest import TestCase
from unittest import TextTestResult
from unittest import TextTestRunner

import BTE.src.Constants as const
import BTE.src.Resources
from BTE.src.DatabaseManagers import DatabaseManagerHyperion
from BTE.src.Helpers import timestamp
from BTE.src.Helpers import replace_escaping_symbols
from BTE.src.CustomExceptions import BTEAssertionError, BTEValueError, BTEKeyError


class BeoTestClassBase(TestCase):
  """ a base class for creation of test classes and running test cases
  @ivar beo_entities: a list of BeoEntity objects which are used by a test class.
  @type beo_entities: BeoEntity
  @ivar arguments: list of arguments for a test method, separated by comma.
  @type arguments: list
  @ivar logger: an object which is responsible for logging
  @type logger: BeoLog
  @ivar testcase_info: an info about the test case. it includes
                            testcase's id, method name and the name of the testcase in Hyperion
  @type testcase_info: a tuple (string, string, string)
  @ivar result: a result of execution of the testcase
  @type result: BeoTestResult
  @ivar diag_tool: a variable for holding information about the diagnostic tool executed with the test
  @type diag_tool: dictionary
  @ivar roles: a list of roles of a resources in a testcase
  @type roles: list of strings
  """

  def __init__(self,
               test_method,
               beo_entities=None,
               arguments=None,
               test_id="test_id",
               logger=None,
               diag_tool_data=None,
               result_id=-1,
               roles=None,
               testcase_name=None):
    """initialise class variables
    @param test_method: a test case to run
    @param beo_entities: a dictionary of BeoEntity and strings objects, which are used by a test case
    @type beo_entities: dictionary. For ex::
      {285:
        {'sw_revision': 'sw_revision',
        'NMM_source': <NMM.src.Resources.STAFBase object at 0x86e450c>,
        'sw_path': 'path'},
      287:
        {'sw_revision': 'sw_revision',
        'NMM_sink': <NMM.src.Resources.STAFBase object at 0x86b3eec>,
        'sw_path': 'path'}
      }

    @param arguments: list of arguments for a test method, separated by comma.
    @type arguments: list
    @param test_id: id of the testcase
    @type test_id: string
    @param diag_tool_data: a variable for holding information about the diagnostic tool executed with the test
    @type diag_tool_data: dictionary
    @param result_id: an id of a result in the database to upload results to
    @type result_id: int
    @param logger: an object which is responsible for logging
    @type logger: BeoLog
    @param roles: a list of roles of a resources in a testcase
    @type roles: list of strings
    @param testcase_name: the name of the testcase in Hyperion
    @type testcase_name: string
    """
    self.tal = None
    self.result = None
    self._test_id = test_id
    if (self._test_id == ""):
      self._test_id = "test_id"

    # add necessary info into BeoLog
    self.logger = logger
    if logger is None:
      self.logger = BeoLog(None, str(self._test_id), result_id=result_id)

    self.diag_tool = diag_tool_data

    sys.exc_clear()

    super(BeoTestClassBase, self).__init__(test_method)

    # from the base class
    self.longMessage = True
    self.maxDiff = None

    self.beo_entities = beo_entities
    if self.beo_entities is None:
      self.beo_entities = {}
    self.roles = []
    if self.roles is not None:
      self.roles = roles

    self.arguments = arguments
    self.testcase_info = (self._test_id, test_method, testcase_name)

    # add necessary info into BeoLog
    self.logger.info("*******************************************")
    self.logger.info("Test Case id: %s" % self.testcase_info[0])
    self.logger.info("Test Case method name: %s" % self.testcase_info[1])
    self.logger.info("Test Case Hyperion's name: %s" % self.testcase_info[2])
    self.logger.info("*******************************************")
    self.logger.info(const.START_TIME)
    self.logger.info("****BeoTestClassBase.__init__ ends********")

  def run(self, result=None):
    """ it assigns the result defined outside of the testcase to a class variable
    and runs the testcase. In this case we can control results (add failures)
    from inside of the test case
    @param result: an object to save result in
    @type result: TestResultAdaptor
    """
    self.logger.info("*************Test Case method starts********")
    self.result = result
    super(BeoTestClassBase, self).run(result)
    self.logger.info("*************Test Case method ends********")
    self.logger.info(const.STOP_TIME)
    self.logger.flush_test_log()

  def delete(self):
    if hasattr(self, "logger") and self.logger is not None:
      self.logger.delete()
      del self.logger


###################################################################################
class BeoTestClass(BeoTestClassBase):
  """ a base class for creation of test classes and running test cases
  this class uses the class L{EntitiesHolder} to create attributes and assign them to correct objects.
  See the help to the class L{EntitiesHolder} for attributes which available in this class
  """

  def __init__(self,
               test_method,
               beo_entities=None,
               arguments=None,
               test_id="",
               logger=None,
               diag_tool_data=None,
               result_id=-1,
               roles=None,
               testcase_name=None):
    super(BeoTestClass, self).__init__(test_method,
                                       beo_entities,
                                       arguments,
                                       test_id,
                                       logger,
                                       diag_tool_data,
                                       result_id,
                                       roles,
                                       testcase_name)

    if len(self.beo_entities) <= 0:
      raise BTEAssertionError("there are no resources for the testcase '%s'" % str(self.testcase_info))

    # it there is only one resource , we will not create  any roles objects
    if len(self.beo_entities) == 1:
      # copy usual attributes
      self.__dict__.update(EntitiesHolder(self.beo_entities.values()[0], self._test_id).__dict__)
      # copy methods
      for method in EntitiesHolder.EXPORT_METHODS:
        setattr(self, method, EntitiesHolder.__dict__[method])

      # setup the verification object
      # pylint: disable=E1101
      if hasattr(self, "ver") and self.ver is not None:
        self.ver.test_class_proxy = BeoTestClassProxy(self)
    else:
      # @todo: refactor this piece of code for the case when >1 resources are provide for a test which requires only one.
      # and does not have roles
      if roles is None:
        raise BTEAssertionError("there are no roles for the testcase '%s'" % str(self.testcase_info))
      if len(roles) == 0:
        raise BTEAssertionError("there are no roles for the testcase '%s'" % str(self.testcase_info))
      for role in roles:
        if role is None:
          raise BTEAssertionError("a role for the testcase '%s' is None. Roles: '%s'" % (str(self.testcase_info), roles))
        role = role.lower()
        # find a resource with that role
        role_found = False
        entities_found = None
        for entities in self.beo_entities.itervalues():
          resource_role = entities.get(const.resource_role, None)
          if resource_role is not None and role in [res_role.lower() for res_role in resource_role if res_role is not None]:
            role_found = True
            entities_found = entities
            break

        if not role_found:
          raise BTEAssertionError("a test case role '%s' is not found at resources roles '%s'" % (role, self.beo_entities))

        self.logger.debug("setting up the target '%s'" % (role))
        setattr(self, role, EntitiesHolder(entities_found, self._test_id, role))

        # setup the verification object
        if getattr(self, role).ver is not None:
          getattr(self, role).ver.test_class_proxy = BeoTestClassProxy(self)

    # copy the temporary module to the log folder
    # A3.src.Menu.Beo4.src.Beo4Support
    modules = self.__module__.split(".")
    if modules[-1].startswith(const.TEMP_TEST_MODULE_NAME):
      module_path = os.path.abspath(sys.modules[self.__module__].__file__)
      shutil.copy(module_path.replace(".pyc", ".py"), self.logger.get_log_folder())
    self._resources_post_setup()
    self.logger.info("********BeoTestClass.__init__ ends***************")

  def tearDown(self):
    """ the method overrides the same method from the base class
    """
    self.logger.info("********BeoTestClass.tearDown starts*************")
    exctype, value = sys.exc_info()[:2]
    if exctype:  # An exception happened, report it
      self.logger.error("Test case stopped because of exception %s: %s" % (exctype, value))
      if exctype == self.failureException:  # Register failure, do some post-processing if needed
        self.on_fail()
    self.logger.info("********BeoTestClass.tearDown ends*************")

  def _resources_post_setup(self):
    """
    Performs additional setup of resources after the test case object has been set up.
    """
    setup_dict = {const.tal_staf: {const.fail_method: self.fail,
                                   const.on_response: self.on_incoming_response}}
    for _res_id, ent_dict in self.beo_entities.items():
      for _eq_name, eq_obj in ent_dict.items():
        if hasattr(eq_obj, "post_setup"):
          eq_obj.post_setup(setup_dict)

  def get_product_name(self):
    """it returns a name of the product on the Device Under Test
    @return: a name of the product on the Device Under Test
    @rtype: a string
    """
    if self.tal is None:
      return None
    return self.tal.get_properties().get(const.product_name, None)

  def on_incoming_response(self, msg):
    """
    Callback function that is invoked when a STAF response message is taken off the response queue.
    This method allows child test case to implement special handling for the
    responses. Children must implement this method themselves.
    @param msg: dict containing a single message, something like this::
                {'responseType': u'AsyncMessage', 'resource': u'192.168.1.74@6550',
                 'name': u'TestMessage', 'RC': u'1', 'new': False, 'arglist': []}
    """
    pass

  def on_fail(self):
    """
    This will be executed on test failure.
    If some special cleanup/finalization step is desired,
    this needs to be overwritten in child classes.
    """
    pass


###################################################################################
class TestResultAdaptor(TextTestResult):
  """a class to convert an interface of test results
  from BeoTestResult to unittest/TextTestResult
  @ivar result: a test result object
  @type result: BeoTestResult
  """
  def __init__(self, test_result,
               stream=None,
               descriptions=1,
               verbosity=1):
    super(TestResultAdaptor, self).__init__(stream, descriptions, verbosity)
    self._results = test_result

  def addError(self, test, err):
    """ it reports an error, but does not fail a test
    @param test: an object of a calling test class
    @type test: TestCase
    @param err: a tuple of values as returned by sys.exc_info().
    """

    TextTestResult.addError(self, test, err)

    # pylint: disable=W0212
    key = "%s.%s" % (test.__class__.__name__, test._testMethodName)

    if (self._results is not None):
      # calculate a unique key
      key = self._calculate_unique_key(key)

      self._results.Error({key: self._exc_info_to_string(err, test)})

  def addFailure(self, test, err):
    """ it report that a test is failed
    @param test: an object of a calling test class
    @type test: TestCase
    @param err: a tuple of values as returned by sys.exc_info().
    """
    TextTestResult.addFailure(self, test, err)

    # pylint: disable=W0212
    key = "%s.%s" % (test.__class__.__name__, test._testMethodName)

    if (self._results is not None):
      # calculate a unique key
      key = self._calculate_unique_key(key)

      self._results.Fail({key: self._exc_info_to_string(err, test)})

  def addSkip(self, test, reason):
    super(TestResultAdaptor, self).addSkip(test, reason)
    self._results.is_skipped = (True, reason)

  def Annotate(self, annotations):
    """it adds annotations to test results
    @param annotations: annotations to add
    @type annotations: dictionary
    """
    self._results.Annotate(annotations)

  def _calculate_unique_key(self, key):
    """it calculates a unique key for the annotation's dictionary
    @param key: an initial key
    @type key: string
    @return: a unique key
    @rtype: string
    """
    annotations = self._results.GetAnnotations()
    counter = 1
    while(key in annotations):
      key = "%s_%s" % (key, counter)
      counter += 1
    return key


###################################################################################
class BeoLog(object):
  """it is responsible for initialising a logging environment. If the parameter target_group is None,
  the object without logger is created, so it is able to print messages only.

  the following commands could be used in code:

    >>> logger.debug("debug message")
    logger.info("info message")
    logger.warn("warn message")
    logger.error("error message")
    logger.critical("critical message")

  @ivar _log_filename: the full name of the log file
  @type _log_filename: string
  @ivar _log_filename_short: the short name of the log file
  @type _log_filename_short: string
  @ivar log_folder: a full name of a folder where log file is stored
  @type log_folder: string
  @cvar DB_MANGER_DUMP_FILENAME_SHORT_NAME: a short name of the file with the dump of db_manager's queries.
  @type DB_MANGER_DUMP_FILENAME_SHORT_NAME: string
  @ivar _logger: a logger object
  @type _logger: Logger
  """

  LOG_FILENAME_SHORT_NAME = "test_case_log.txt"
  DB_MANGER_DUMP_FILENAME_SHORT_NAME = "db_manger_dump_file.txt"

  def __init__(self, log_root="", log_folder_name="", log_filename="", use_time_stamp=True, result_id=-1):
    """initializes logging environment
    @param log_root: a root folder of a new log folder
    @type log_root: string
    @param log_folder_name: a short name of a folder where logs will be placed to
    @type log_folder_name: string
    @param use_time_stamp: whether to use a timestamp to make the folder unique
    @type use_time_stamp: boolean
    @param log_filename: a name of a log file which will be used to log info, for ex. "log.txt"
    @type log_filename: string
    """
    # handle port number if it is assigned, for example, 192.168.1.1:800_6
    log_folder_name = replace_escaping_symbols(log_folder_name)
    log_filename = replace_escaping_symbols(log_filename)

    self._log_filename_short = self.LOG_FILENAME_SHORT_NAME
    if (log_filename != ""):
      self._log_filename_short = log_filename

    # add a time stamps to the name
    # if result_id is not -1, it will be always used for log folder name instead of timestamp
    if result_id != -1:
      log_folder_name = log_folder_name + "." + str(result_id)
    elif (use_time_stamp and log_folder_name != ""):
      log_folder_name = log_folder_name + "." + time.strftime("%Y_%m_%d_%H_%M_%S")

    if (log_folder_name == ""):
      log_folder_name = time.strftime("%Y_%m_%d_%H_%M_%S")

    # create a folder for log files
    if (log_root is None or log_root == ""):
      log_root = tempfile.gettempdir()
    self.log_folder = os.path.join(log_root, log_folder_name)
    if (not os.path.exists(self.log_folder)):
      os.mkdir(self.log_folder)

    # create a log file name
    self._log_filename = os.path.join(self.log_folder, self._log_filename_short)

    self._logger = logging.getLogger(self._log_filename)
    self._logger.setLevel(logging.DEBUG)
    self._logger.propagate = 0
    # create a handler only if there is no one.
    if len(self._logger.handlers) == 0:
      handler = logging.FileHandler(self._log_filename, encoding='utf-8')
      formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
      handler.setFormatter(formatter)
      self._logger.addHandler(handler)

    self._result_id = result_id
    self._db_manager = None
    try:
      if (self._result_id > 0):
        self._db_manager = DatabaseManagerHyperion(os.path.join(self.log_folder, self.DB_MANGER_DUMP_FILENAME_SHORT_NAME))
        self._db_manager.start_log_thread()
    # pylint: disable=W0703
    except Exception as e:
      self.warn("cannot create db manager: %s" % e)

  def delete(self):
    """it deletes/cleanup the instanse of the class
    """
    if (self._db_manager is not None):
      # without the timeout the exception 'IOError: [Errno 32] Broken pipe' can appear
      time.sleep(0.1)
      self._db_manager.delete()
      del self._db_manager
    # close handlers
    for h in self._logger.handlers:
      try:
        h.close()
      except ValueError as e:
        # ignoring some errors
        if str(e).find("operation on closed file") == -1:
          raise BTEValueError(e)
      except KeyError as e:
        if str(e).find("logging.FileHandler") == -1:
          raise BTEKeyError(e)

  def flush_test_log(self):
    """it flushes the test log
    """
    if (self._db_manager is not None):
      self._db_manager.stop_log_thread()

  def _log_message(self, message, message_type):
    """prints info into a log and into stdout
    """
    try:
      if isinstance(message, dict):
        message = json.dumps(message, ensure_ascii=False).decode("utf-8")
      elif isinstance(message, tuple) or isinstance(message, list) or isinstance(message, set):
        msg = ''
        for m1 in message:
          if isinstance(m1, str):
            msg += m1 + ","
          elif isinstance(m1, unicode):
            dcmsg = m1.encode("utf-8")
            msg += dcmsg + ","
          else:
            msg += str(m1) + ","
        message = "".join(msg.decode("utf-8"))[:-1]
      elif isinstance(message, types.StringTypes):
        message = message.decode("utf-8")
      else:
        message = str(message)
    except (TypeError, UnicodeError) as exc:
      print("***Error: An exception happened during converting a message to a string: %s. Skipping the message" % exc)

    tstamp = timestamp()
    try:
      print(u"%s - %s - %s" % (tstamp, message_type.upper(), message))
    except UnicodeError as exc:
      # if we cannot print the message into std out, there is little sense in trying to upload it into DB or logger output
      print("***Error: An exception happened during printing a message to stdout: %s. Skipping the message.Printing it as list of symbols" % exc)
      try:
        print([ch for ch in message])
      # pylint: disable=W0703
      except Exception as exc:
        print("***Error: Cannot print a message. Exception: %s" % exc)
      return

    if (self._logger is not None):
      if message_type == const.message_type_info:
        self._logger.info(message)
      elif message_type == const.message_type_debug:
        self._logger.debug(message)
      elif message_type == const.message_type_warn:
        self._logger.warn(message)
      elif message_type == const.message_type_error:
        self._logger.error(message)
      elif message_type == const.message_type_critical:
        self._logger.critical(message)

    if (self._db_manager is not None):
      try:
        self._db_manager.upload_log_entry(tstamp, self._result_id, message, message_type)
      except UnicodeError as exc:
        try:
          self._db_manager.upload_log_entry(tstamp, self._result_id, message.encode('utf-8'), message_type)
        # pylint: disable=broad-except
        except Exception as exc:
          msg = "cannot log a message into the db: %s" % exc
          print(msg)
          self._logger.warn(msg)
      # pylint: disable=broad-except
      except Exception as exc:
        msg = "cannot log a message into the db: %s" % exc
        print(msg)
        self._logger.warn(msg)

  def info(self, message):
    """prints info into a log and into stdout"""
    self._log_message(message, const.message_type_info)

  def debug(self, message):
    """prints debug into a log and into stdout"""
    self._log_message(message, const.message_type_debug)

  def warn(self, message):
    """prints warn into a log and into stdout"""
    self._log_message(message, const.message_type_warn)

  def error(self, message):
    """prints error into a log and into stdout"""
    self._log_message(message, const.message_type_error)

  def critical(self, message):
    """prints critical into a log and into stdout"""
    self._log_message(message, const.message_type_critical)

  def get_log_folder(self):
    """returns a path to the folder where log are stored
    @return: a path to the folder where log are stored
    @rtype: string
    """
    return self.log_folder

  def get_log_file(self):
    """returns a path to the name of the file where log are stored
    @return: a path to the name of the file where log are stored
    @rtype: string
    """
    return self._log_filename


###################################################################################
class BeoLogProxy():
  """it is a proxy class for BeoLog
  it allows us to print an additional info, for ex. about an calling obj, into a message
  """
  def __init__(self, beo_logger, obj_info=""):
    """constructor
    @param beo_logger: an instance of the class BeoLog
    @type beo_logger: BeoLog
    @param obj_info: information about an object which owns the current instance in the form::
            "%s,%s,%s" % (device_name, role, resource_name)))

    @type obj_info: string
    """
    self._logger = beo_logger
    self._obj_info = obj_info
    if self._logger is None:
      self.info = self._print
      self.debug = self._print
      self.warn = self._print
      self.error = self._print
      self.critical = self._print

  def delete(self):
    """it deletes/cleanup the instanse of the class
    """
    if self._logger is not None:
      self._logger.delete()

  def flush_test_log(self):
    """it flushes the test log
    """
    self._logger.flush_test_log()

  def set_obj_info(self, obj_info):
    """ it sets the new object info
    @param obj_info: the new object info
    @type obj_info: string
    """
    self._obj_info = obj_info

  # pylint: disable=E0202
  def info(self, message):
    """prints info into a log and into stdout"""
    self._logger.info("[%s]: %s" % (self._obj_info, message))

  def debug(self, message):
    """prints debug into a log and into stdout"""
    self._logger.debug("[%s]: %s" % (self._obj_info, message))

  def warn(self, message):
    """prints warn into a log and into stdout"""
    self._logger.warn("[%s]: %s" % (self._obj_info, message))

  def error(self, message):
    """prints error into a log and into stdout"""
    self._logger.error("[%s]: %s" % (self._obj_info, message))

  def critical(self, message):
    """prints critical into a log and into stdout"""
    self._logger.critical("[%s]: %s" % (self._obj_info, message))

  def get_log_folder(self):
    """returnes folderpath where log are stored
    """
    return self._logger.get_log_folder()

  def get_log_file(self):
    """returns a path to the name of the file where log are stored
    @return: a path to the name of the file where log are stored
    @rtype: string
    """
    return self._logger.get_log_file()

  def _print(self, message):
    print "%s - %s" % (timestamp(), message)


###################################################################################
class BeoTextTestRunner (TextTestRunner):
  """A test runner class that displays results in textual form.
  It prints out the names of tests as they are run, errors as they
  occur, and a summary of the results at the end of the test run.
  @ivar test_results: a test result object
  @type test_results: BeoTestResult
  @ivar stream: a stream object to write results in
  @type stream: BeoWritelnDecorator
  """

  def __init__(self, test_result=None, stream=None, descriptions=1, verbosity=1):
    super(BeoTextTestRunner, self).__init__(stream, descriptions, verbosity)

    self.stream = BeoWritelnDecorator(stream)
    self.test_results = test_result

  def _makeResult(self):
    """create and return an object for saving test execution results
    @return: a unittest Results object
    @rtype: TestResultAdaptor
    """
    return TestResultAdaptor(self.test_results, self.stream, self.descriptions, self.verbosity)


###################################################################################
class BeoWritelnDecorator(object):
  """Used to decorate file-like objects with a handy 'writeln' method
  @ivar file_name: a name of a log file to write results into
  @param file_name: string
  """

  def __init__(self, file_name):
    self.file_name = file_name

  def writeln(self, message=None):
    """it writes a line to a file
    @param message: a message to be written
    @type message: string
    """
    if message is not None:
      with open(self.file_name, 'a') as f:
        f.write(message)
        f.write('\n')

  def write(self, message=None):
    """it writes a string to a file
    @param message: a message to be written
    @type message: string
    """
    if message is not None:
      with open(self.file_name, 'a') as f:
        f.write(message)

  def flush(self):
    pass


###################################################################################
class BeoTestResult(object):
  """ the class maintains all information about execution of a single testcase
  @ivar _outcome: an outcome of test execution
  @type _outcome: string
  @ivar _annotations: annotations to a test execution
  @type _annotations: dictionary
  @ivar is_skipped: a tuple, indicating whether a test is skipped and a reason
  @type is_skipped: a tuple (boolean, string)
  """
  def __init__(self):
    self._outcome = const.UNTESTED
    self._annotations = {}
    self.is_skipped = (False, "")

  def __del__(self):
    del self._annotations

  def Annotate(self, annotations):
    """it adds annotations to a dictionary
    @param annotations: annotations to add
    @type annotations: dictionary
    """
    self._annotations.update(annotations)

  def GetAnnotations(self):
    """it returns annotations
    @return: annotations
    @rtype: dictionary
    """
    return self._annotations

  def SetOutcome(self, outcome, annotations=None):
    """it sets result of execution: failed, passed etc.
    @param outcome: the result of execution
    @type outcome: string
    @param annotations: annotations to outcome
    @type annotations: dictionary
    """
    if annotations is None:
      annotations = {}
    self._outcome = outcome
    self.Annotate(annotations)

  def Pass(self, annotations=None):
    """it sets result of execution: passed
    @param annotations: annotations to outcome
    @type annotations: dictionary
    """
    if annotations is None:
      annotations = {}
    self.SetOutcome(const.PASSED, annotations)

  def Fail(self, annotations=None, fail_status=const.FAILED):
    """it sets result of execution: faild
    @param annotations: annotations to outcome
    @type annotations: dictionary
    """
    if annotations is None:
      annotations = {}
    self.SetOutcome(fail_status, annotations)

  def Error(self, annotations=None, error_status=const.ERROR):
    """it sets result of execution: error
    @param annotations: annotations to outcome
    @type annotations: dictionary
    """
    if annotations is None:
      annotations = {}
    self.SetOutcome(error_status, annotations)

  def Untested(self, annotations=None):
    """it sets result of execution: untested
    @param annotations: annotations to outcome
    @type annotations: dictionary
    """
    if annotations is None:
      annotations = {}
    self.SetOutcome(const.UNTESTED, annotations)

  def GetOutcome(self):
    """it returns result of execution: faild, passed etc.
    @return: result of execution
    @rtype: string
    """
    return self._outcome


###################################################################################
class EntitiesHolder(object):
  """the class which holds beo_entities for BeoTestClasses

  @ivar export_methods: names of class methods which are exported
  @type export_methods: list of string
  @ivar tal: Target Abstraction Layer -- an object, which is responsible for communication with a target
  @type tal: TALBase
  @ivar nav: Navigation -- an object, which is responsible for navigation in a target
  @type nav: NavigationBase
  @ivar ver: Verification -- an object, which is responsible for verification of actual results
  @type ver: VerificationBase
  @ivar remote_control: Remote Control -- an object, which is responsible for conversion string representation of IR telegrams to hex code
  @type remote_control: RemoteControl
  @ivar ir_receiver: IR receiver  -- an object, which is responsible for receiving IR telegram and sending them to a PC
  @type ir_receiver: IRReceiver
  @ivar vm: video modulator -- an object which is responsible for playing DVB content
  @type vm: VideoModulator
  @ivar sound_card: sound card -- an audio card to receive and verify sound
  @type sound_card: BTE.src.Resources.SoundCard
  @ivar bt_sound_card: sound card -- an bluetooth audio device to send sound out
  @type bt_sound_card: BTE.src.Resources.SoundCard
  @ivar sw_path: a path to the built sw provided by a BuiltBot
  @type sw_path: string
  @ivar sw_revision: a revision of the sw, provided by a BuiltBot
  @type sw_revision: string
  @ivar Q882: Quantum Generator -- an object, which is responsible for sending test content to HDMI ports
  @type Q882: Quantum882XMLRPC
  @ivar a1con: a1 controller -- an object which is responsible for management of
          tv of the A1 type (old tv platform)
  @type a1con: BTE.src.Resources.A1_Controller
  @ivar SFU_Control: SFU Controller -- an object which is responsible for management
          of a Rohde & Schwarz SFU
  @type SFU_Control: BTE.src.Resources.SFU_Controller
  @ivar serial_output: serial output -- an object which is responsible for downloading serial output for a target
  @type serial_output: SerialOutput
  @ivar acm_camera: ACM camera  -- an object, which manages an ACM camera
  @type acm_camera: BTE.src.Resources.ACMCamera
  @ivar discharge_relay: an object which is responsible for discharge some devices on a board
  @type discharge_relay: InternalResource
  @ivar nav_ltap: an object, which is responsible for navigation by sending real IR telegrams
  @type nav_ltap: NavigationLTAP
  @ivar tal_http: Target Abstraction Layer for http -- an object, which is responsible for communication with a target through the http protocol
  @type tal_http: TALHTTP
  @ivar ext_storage: an external HDD, connected to the TV
  @type ext_storage: InternalResource
  @ivar cam_card: an cam card connected to the TV
  @type cam_card: InternalResource
  @ivar stand: a mock object of a stand
  @type stand: Stand
  @ivar btb: a mock object of a Business to Business STB
  @type btb: BtB
  @ivar panel: a mock object of a plasma panel, which could be connected to BeoSystem4
  @type panel: Panel
  @ivar apx_control: apx controller -- an object which is responsible for management
          of a audio precision apx sound tester
  @type apx_control: APx_Controller
  @ivar pl_sound_detector: an object to read/write to/from the serial(UART) port
    to detect the state of the sound from PL channels
    through a special B&O device
  @type pl_sound_detector: PLSoundDetector
  @ivar tal_beoportal: a tal object of beoportal to use BeoPortal as an equipment
  @type tal_beoportal: BeoPortalServiceContainer
  @ivar selenium_server: an object to get an ip address and port of a PC where
    selenium server is running
  @type selenium_server: InternalResource
  @ivar webcam_controller: webcam_controller -- an object which connects via XMLRPC to get information from a webcam
  @type webcam_controller: webcam_controller
  @ivar itunes: an object to operate iTunes on a Mac OS PC
  @type itunes: ITunes
  @ivar router_wlan: an object representing a wlan router.
  @type router_wlan: InternalResource
  @ivar router_lan: an object representing a lan router.
  @type router_lan: InternalResource
  @ivar fep: a mock of fep
  @type fep: ASETurnKeyFEP
  @ivar chromecast: an object representing chromecast
  @type chromecast: Chromecast
  @ivar tal_adb: Target Abstarction Layer to communicate with DUT through Android Debug Bridge
  @type tal_adb: ADB
  """
  RETRIEVE_SYS_LOG_NAME = "retrieve_sys_log"
  RETRIEVE_REPORTS_NAME = "retrieve_reports"
  EXPORT_METHODS = [RETRIEVE_SYS_LOG_NAME, RETRIEVE_REPORTS_NAME]

  def __init__(self, entities, test_id, role=""):
    """ constructor
    @param entities: a dictionary of entities
    @type entities: dictionary
    @param role: a role of the resource in testcase
    @type role: string
    @param test_id: an id of a testcase
    @type test_id: string
    """
    self.tal = entities.get(const.tal, None)
    self.nav = entities.get(const.navigation, None)
    self.ver = entities.get(const.verification, None)
    self.remote_control = entities.get(const.remote, None)
    self.bt_remote_control = entities.get(const.bt_remote, None)
    self.ir_receiver = entities.get(const.ir_receiver, None)
    self.vm = entities.get(const.video_modulator, None)
    self.sound_card = entities.get(const.sound_card, None)
    self.bt_sound_card = entities.get(const.bt_sound_card, None)
    self.sw_path = entities.get(const.sw_path, None)
    self.sw_revision = entities.get(const.sw_revision, None)
    self.Q882 = entities.get(const.quantum_generator, None)
    self.a1con = entities.get(const.a1_controller, None)
    self.SFU_Control = entities.get(const.sfu_controller, None)
    self.PTS_Control = entities.get(const.pts_controller, None)
    self.serial_output = entities.get(const.serial_output, None)
    self.acm_camera = entities.get(const.acm_camera, None)
    self.discharge_relay = entities.get(const.discharge_relay, None)
    self.tal_http = entities.get(const.tal_http, None)
    self.nav_ltap = None
    self.ext_storage = entities.get(const.ext_storage, None)
    self.cam_card = entities.get(const.cam_card, None)
    self.stand = entities.get(const.stand, None)
    self.btb = entities.get(const.btb, None)
    self.panel = entities.get(const.panel, None)
    self.apx_control = entities.get(const.apx_controller, None)
    self.apple_communicator = entities.get(const.apple_communicator, None)
    self.pl_sound_detector = entities.get(const.pl_sound_detector, None)
    self.tal_beoportal = entities.get(const.tal_beoportal, None)
    self.selenium_server = entities.get(const.selenium_server, None)
    self.tal_staf = entities.get(const.tal_staf, None)
    self.webcam_controller = entities.get(const.webcam_controller, None)
    self.router_wlan = entities.get(const.router_wlan, None)
    self.router_lan = entities.get(const.router_lan, None)
    self.bonjour_browser = entities.get(const.bonjour_browser, None)
    self.dse = entities.get(const.dse, None)
    self.dlna_server = entities.get(const.dlna_server, None)
    self.fep = entities.get(const.FEP, None)
    self.chromecast = entities.get(const.CHROMECAST, None)
    self.tal_adb = entities.get(const.TAL_ADB, None)

    resource_name = entities.get(const.resource_name, "")
    # NavigationLTAP is bound to LTAP
    # If there is an ltap device in the system, NavigationLTAP is present by default
    if entities.get(const.ltap, None) is not None:
      self.nav_ltap = BTE.src.Resources.NavigationLTAP({const.ip: None, const.port: None})
      self.nav_ltap.setup(entities)
      self.nav_ltap.logger.set_obj_info("%s,%s,%s" % (const.ltap, role, resource_name))

    if self.nav is not None:
      self.nav.logger.set_obj_info("%s,%s,%s" % (const.navigation, role, resource_name))

    if self.ver is not None:
      self.ver.logger.set_obj_info("%s,%s,%s" % (const.verification, role, resource_name))

    if self.tal is not None:
      self.tal.logger.set_obj_info("%s,%s,%s" % (const.tal, role, resource_name))
      # disable translation
      self.tal.text_translation_disable()

    if self.serial_output is not None:
      self.serial_output.logger.set_obj_info("%s,%s,%s" % (const.serial_output, role, resource_name))

    # copy and delete the core dumps only for regular test cases from the Hyperion DB
    # (ones, which have a correct id, as integer and not in const.SERVICE_TESTCASES) and (tal is not None and has correct attributes)
    try:
      if test_id is not None:
        if (((isinstance(test_id, types.IntType) and test_id not in const.SERVICE_TESTCASES) or
             (isinstance(test_id, types.StringTypes) and test_id.isdigit() and int(test_id) not in const.SERVICE_TESTCASES)) and
             (self.tal is not None and hasattr(self.tal, "get_coredumps"))):
          self.tal.get_coredumps()
          self.tal.remove_coredumps()
    # crashing in get_coredumps should not influence test case execution
    # so we need to catch all exception.
    # if there is a problem with a DUT, it will be discovered later.
    # pylint: disable=broad-except
    except Exception as exc:
      # logger is not available here
      print("An exception happened in 'get-remove coredumps' functionality: %s" % exc)
    except:
      tp, value, _traceback = sys.exc_info()
      print("An unknown exception happened. Type: %s, Value: %s. Continuing" % (tp, value))

  def get_entities(self):
    """
    Returns a list of entities an EntitiesHolder instance has.
    """
    l = []
    for i in self.__dict__.items():
      # if isinstance(i[1], BTE.src.Resources.BeoEntity):
      if hasattr(i[1], 'staf_enabled'):  # Just a hack to make sure that an attribute eally is a BeoEntity instance
        l.append(i)
    return l

  def retrieve_sys_log(self, test_results):
    """it retrieves a syslog from a DUT (Device Under Test)
    @param test_results: a result of execution of a test case
    @type test_results: BeoTestResult
    @return: a full path to the retrieved sys log
    @rtype: string
    """
    try:
      if self.tal is not None:
        return self.tal.get_syslog()
    # pylint: disable=W0703
    except Exception:
      if test_results is not None:
        test_results.Annotate({"Sys log retrieve error": "".join(traceback.format_exception(*sys.exc_info()))})
      # get minicom output
      if self.serial_output is not None:
        # get usual output
        if not self.serial_output.get_output_file() and test_results is not None:
          test_results.Annotate({"Serial output retrieve": "It is impossible to retrieve serial output"})
        # get FEP output
        if not self.serial_output.get_output_FEP_file() and test_results is not None:
          test_results.Annotate({"FEP serial output retrieve": "It is impossible to retrieve FEP serial output"})
    return ""

  def retrieve_reports(self, test_results, result_id):
    """
    Retrieves report files from a DUT
    """
    if self.tal is not None and hasattr(self.tal, "get_reporting"):
      self.tal.get_reporting(result_id)


class BeoTestClassProxy(object):
  """the class contains only pointer to some assertion methods from the BeotTestClass
  the class is used at the verification class
  the class doesn't follow the classic 'Proxy' pattern
  """
  def __init__(self, test_class_instance):
    """ constructor
    @param test_class_instance: an instance of a testcase
    @type test_class_instance: TestCase
    """
    self._test_case = test_class_instance

    # get all available valid assert methods
    assertmethods = [i for i in TestCase.__dict__.keys() if (i.startswith("assert") and i.find("_") == -1 and i.find("Equals") == -1)]

    # set assert methods
    for method in assertmethods:
      setattr(self, method, getattr(self._test_case, method))

  def get_test_case(self):
    return self._test_case


class BeologTest(TestCase):
  """unittest for the class BeoLog"""

  def setUp(self):
    """setup"""
    self.testsList = []
    self.bl = BeoLog()
    print(self.bl._log_filename)
    self.testsList = [1234,
                      "string",
                      {"string": "测试測試"},
                      '{"string": "测试測試"}',
                      ("string", "测试測試"),
                      ('ää', 'öö'),
                      (u'ää', 'öö'),
                      (u'ää', u'öö'),
                      ("测试測試", 'öö'),
                      ("测试測試", u'öö'),
                      ("测试測試", "测试測試"),
                      (123, 'öö'),
                      (123, 456),
                      ((3, 4), "测试測試"),
                      {'ONE': '2341', 'TWO': '9102'},
                      {u'ONE': '2341', 'TWO': '9102'},
                      {u'ONE': u'2341', 'TWO': '9102'},
                      {u'ONE': u'2341', u'TWO': '9102'},
                      {u'ONE': u'2341', 'TWO': u'9102'},
                      {u'ONE': 2341, 'TWO': u'9102'},
                      ['ABCD', 'EFGH'],
                      [u'ABCD', 'EFGH'],
                      [u'ABCD', u'EFGH'],
                      ['ää', 'öö'],
                      [u'ää', 'öö'],
                      [u'ää', u'öö'],
                      [123, 456],
                      set(['ABCD', 'EFGH']),
                      set([123, 456]),
                      set(['ää', 'öö']),
                      set(["string", "测试測試"]),
                      set([123, 'öö'])]

  def tearDown(self):
    """teardown"""

  def test_log_message(self):
    """ testing different messages

    verifying that it doesn't crash on coding-decoding different types of messages
    """
    message_type = "debug"
    for index, message in enumerate(self.testsList):
      time.sleep(0.1)
      print(index)
      self.bl._log_message(message, message_type)


# if __name__ == "__main__":
# #===============================================================================
# # unittests
# #===============================================================================
#   from unittest import TestLoader
#   # #
#   ed_suite = TestLoader().loadTestsFromTestCase(BeologTest)
#   TextTestRunner(verbosity=3).run(ed_suite)
