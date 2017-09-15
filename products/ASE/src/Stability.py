'''
Created on Jul 12, 2017

@author: thomas
'''
import time

import Common.src.Helpers as Helpers
import ASE.src.Helpers as ASEHelpers
from ASE.src.SourceHandler import SourceHandler
import Common.src.Constants as comm_const
import Common.ASE.CommonLib.src.Constants as ase_const
from BTE.src.CommonTestClasses import BeoTestClass


class Stability(BeoTestClass):
  """
  Class for testing stability of simple functions on ASE
  """
  # pylint:disable=E1101

  def setUp(self):
    self.tal_http.debug = True
    # clear MUSIC queue
    # Helpers.clear_queue(self.tal_http, Helpers.PlayQueueName.MUSIC)

    self._deezer_account = ASEHelpers.get_deezer_account(self.tal)
    self._tunein_account = comm_const.TUNEIN_ACCOUNT

    self._src_handler = SourceHandler

    self._deezer_client_helper = ASEHelpers.DeezerClientHelper(self.tal_http, self.logger, self._deezer_account)
    # self._tunein_client = ASEHelpers.TuneInClientHelper(self.tal_http, self.logger, self._tunein_account)
    # self._sound_verification = ASEHelpers.SoundVerification(self.logger, self.sound_card, self.tal_http, self.assertFalse, self.assertEqual)
    # self._dlna_client = ASEHelpers.DLNAClientHelper(self.tal_http, self.logger)
    self._verification = ASEHelpers.Verification(self.logger,
                                                 self.tal_http,
                                                 self.assertFalse,
                                                 self.assertEqual)

    # log into deezer with a correct account
    if not self._deezer_client_helper.is_logged_in():
      self._deezer_client_helper.logout()
      # Needs a little time between logout and login.
      time.sleep(3)
      self._deezer_client_helper.login()

    self.setUp_done()

  def tearDown(self):
    self.tearDown_starts()
    if self.tal_http.is_listening_to_notifications:
      self.tal_http.stop_listening_to_notifications()
    self.tal_http.stream_stop()

  def clear_playqueue_add_tracks_and_play_repeat(self):
    """
    Tests stabillity of clearing and adding to playqueue
    1. Clear queue
    2. Set source
    3. Try to play first track in playqueue
    4. repeat 1-3
    """
    for itt in range(1, 1000):
      self.logger.info("Clear playqueue on DUT add tracks and start play first added Deezer track")
      self._play_deezer()
      self.logger.info("Loop number %s" % itt)

  def switch_source_repeat(self):
    """
    Test the stability of source switching
    1. Set source
    2. Verify source switch
    3. repeat 1-2
    """
    active_source_list = [comm_const.SourceJidPrefix.BLUETOOTH, comm_const.SourceJidPrefix.DEEZER, comm_const.SourceJidPrefix.DLNA,
                          comm_const.SourceJidPrefix.GOOGLECAST, comm_const.SourceJidPrefix.SPOTIFY, comm_const.SourceJidPrefix.RADIO]
    self._play_deezer()

    for itt in range(1, 1000):
      self.logger.info("Loop number %s" % itt)
      for active_source in active_source_list:
        self.tal_http.start_listening_to_notifications(50, -1)
        self.tal_http.set_active_source(active_source)
        self._verification.verify_active_source(active_source, False, True)
        notifications = self.tal_http.get_notifications(30)
        for notification in notifications:
          self.logger.info(notification)
          if notification.type == ase_const.SOURCE_NOTIFICATION:
            correct_notification = True
        ASEHelpers.verify_notification_received(self.logger, correct_notification, ase_const.SOURCE_NOTIFICATION)
        self.tal_http.stop_listening_to_notifications()

  def play_pause_repeat(self):
    """
    Test stability of play pause functionality
    1. Pause stream
    2. Verify pause
    3. Play stream
    4. Verify play
    5. repeat 1-4
    """
    correct_notification = False
    self._play_deezer()
    add_more_tracks = 0
    time.sleep(5)

    for itt in range(1, 1000):
      add_more_tracks = add_more_tracks + 1
      if add_more_tracks == 10:
        self._play_deezer()
        add_more_tracks = 0
      self.logger.info("Loop number %s" % itt)
      self.tal_http.start_listening_to_notifications(50, -1)
      self.logger.info("1. Pause stream")
      self.tal_http.stream_pause()
      time.sleep(5)
      notifications = self.tal_http.get_notifications(50)
      self.logger.info("2. Verify pause")
      for notification in notifications:
        self.logger.info(notification)
        if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None) == "pause":
          correct_notification = True
      ASEHelpers.verify_notification_received(self.logger, correct_notification, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', "pause")
      self.tal_http.stop_listening_to_notifications()
      correct_notification = False

      self.tal_http.start_listening_to_notifications(50, -1)
      self.logger.info("3. Play stream")
      self.tal_http.stream_play()
      time.sleep(5)
      notifications = self.tal_http.get_notifications(50)
      self.logger.info("4. Verify play")
      for notification in notifications:
        self.logger.info(notification)
        if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None) == "play":
          correct_notification = True
      ASEHelpers.verify_notification_received(self.logger, correct_notification, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', "play")
      self.tal_http.stop_listening_to_notifications()
      correct_notification = False
      self.tal_http.stop_listening_to_notifications()

  def _play_deezer(self):
    """
    Clears music playqueue and adds two deezer tracks of wich the first will start to play
    """
    Helpers.clear_queue(self.tal_http, Helpers.PlayQueueName.MUSIC)  # clear MUSIC queue
    current_sources = self.tal_http.get_active_sources(True)
    self.tal.logger.info("current sources: %s" % current_sources)
    self.tal_http.send_http_command_delete(comm_const.BEOZONE_PLAYQUEUE)
    self.tal_http.logger.info("***clear queue finish***")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    play_ids = self._deezer_client_helper.add_tracks_to_play_queue(5)
    self.tal_http.play_queue_play(play_ids[0])
    time.sleep(5)

if __name__ == "__main__":
  """ """
#   #===============================================================================
#   # # creation of an xml file with test cases
#   #===============================================================================
#   import sys
#   from Common.src.Helpers import create_tc_creator_xml_file, update_tc_xml_file
# #   output_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/TestCasesCreate.xml"
# #   create_tc_creator_xml_file(sys.modules[__name__], output_file)
#   input_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/DLNAClient_tc.xml"
#   start_path = "/home/vsu/svn/beotest/Trunk/products"
#   update_tc_xml_file(sys.modules[__name__], input_file, start_path)
  # integration test
  from BTE.src.TestRunner import BeoTestRunner
  from BTE.src.CommonTestClasses import BeoTestResult

  test_case_arguments = ""
  result = BeoTestResult()
  target_name = {"System_test_Box12_BS35": {}}
  test_id = None
  test_module_name = "ASE.src.Stability"
  test_class_name = "Stability"

  test_case_name = "switch_source_repeat"
#   test_case_name = "play_pause_repeat"
#   test_case_name = "dlna_as_last_played_source_after_tunein_no_playqueue"

  test_case_known_error = None
  test_case_setup = None
  test_case_script = None
  test_case_cleanup = None

  tr = BeoTestRunner(result, target_name, test_id, test_module_name, test_class_name, test_case_name, test_case_arguments,
                     test_case_setup, test_case_script, test_case_cleanup, local_run=False)
  tr.run()
