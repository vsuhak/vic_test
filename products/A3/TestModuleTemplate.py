"""
  @copyright: 2012 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S

  A short description of the module

  @author: *INITIALS*
  update in master
"""
from BTE.src.CommonTestClasses import BeoTestClass
import Common.VideoEngine.CommonLib.src.Constants as a3_const
from Common.VideoEngine.CommonLib.src.Helpers import CommonMethods
from A3.src.MediaPlayer.src.MPParsing import MPParsing
from Common.VideoEngine.DVB.src.Tuning import Tuning
from A3.src.PUC.src import PUC
from Common.VideoEngine.CommonLib.src.MenuItem import FactoryMenu

class TestClass(BeoTestClass):
  """
  Description of the TestClass
  """

  def setUp(self):
    """
    Setup
    """
    # *This function is used for setting up general preconditions before the test case starts.*


  def tearDown(self):
    """
    Tear down
    """
    # *This function is used cleaning up after the test case is done.*

  def TestCase1(self):
    # *All information from the following comment field will be used by the Hyperion web server*
    """
    Description of the purpose with this test case.

    Steps: #Describe the steps in the test.
    1: Step 1
    2: Step 2
    3: Step 3
    4: Step 4
    5: Step 5
    ...
    N: Step N

    Hyperion::
      @argumentDescription: A short description of the arguments used by the test script (*Optional field*)
                           (Arguments can be received with self.arguments)
      @Role1: TV
      @Equipment1: [equipment1, equipment2] (*Optional field*)
    """

    # *Write the code which support the steps described*

  def TestCase2(self):
    # *All information from the following comment field will be used by the Hyperion web server*
    """
    Description of the purpose with this test case.

    Steps: #Describe the steps in the test.
    1: Step 1
    2: Step 2
    3: Step 3
    4: Step 4
    5: Step 5
    ...
    N: Step N

    Hyperion::
      @argumentDescription: A short description of the arguments used by the test script (*Optional field*)
                           (Arguments can be received with self.arguments)
      @Role1: TV
      @Equipment1: [equipment1, equipment2] (*Optional field*)
    """

    # *Write the code which support the steps described*

  def _helper_method(self, Arg1, ArgN):
    # *None of the information  from the following comment field will be used by the Hyperion web server*
    """
    This is a helper method for the test case method
    @param Arg1: Description of the argument
    @type Arg1: Ex string or integer
    @param ArgN: Description of the argument
    @type ArgN: Ex string or integer
    @return: Description of what the method will return
    @rtype: Ex string or integer
    """

    # *Write the code for the helper method*
    # *The helper method should be privat hence the "_"*
    # *If you want to use the method from another class*
    # *It should be moved to the common area and made public*

# if __name__ == "__main__":
#  """ """
#  #integration test
#  from BTE.src.TestRunner import BeoTestRunner
#  from BTE.src.CommonTestClasses import BeoTestResult
#
#  test_case_arguments = "ARGUMENTS FOR THE TEST CASE"
#  result = BeoTestResult()
#  target_name = {"TARGET_NAME_FROM_ENVIRONMENTLAB_PY":{}}
#  test_id = None
#  test_module_name = "A3.path.path"
#  test_class_name = "TestClass"
#  test_case_name = "TestCase1"
#
#  test_case_setup = None
#  test_case_script = None
#  test_case_cleanup = None
#
#  tr = BeoTestRunner(result,target_name,test_id,test_module_name, test_class_name, test_case_name, test_case_arguments ,
#               test_case_setup, test_case_script, test_case_cleanup)
#  tr.run()
