"""
  Test cases for the BeoLink source

  @copyright: 2015 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: VSU
"""
import os
import time
import datetime
import json

import Common.src.Constants as comm_const
import Common.ASE.CommonLib.src.Constants as ase_const
import Common.src.Helpers as Helpers
import ASE.src.Helpers as ASEHelpers
import Common.ASE.CommonLib.src.PlayBack as PlayBack

from selenium.common.exceptions import NoSuchElementException
from BTE.src.CommonTestClasses import BeoTestClass
from Common.src.ITunes import ITunesState
from Common.ASE.CommonLib.src.Webpage import webpage_get


class BeoLink(BeoTestClass):
  """ the class for test cases for the source BeoLink.
  They are a kind of smoke tests for Multiroom functionality

  Leader - a product which runs the player and have control over it
  Follower - a product, which receives an audio stream from the Leader and play it

  @todo: Take a look at if it is necessary go repeat some test cases
  for all available sources

  @todo: if there is a functionality to reverse roles: Leader <-> Follower
  test changes
  test change #2
  test change #3
  """
#   # Settings for debugging
  _LONG_TIME = (15 * 60)  # 15 minutes
  # Settings for testing
#   _LONG_TIME = (12 * 60 * 60)  # 12 hours

  # full paths of file on ftp server
  _ASE_SW_FTP = "ftp://stz07ww03.bang-olufsen.dk"

  _STRING = "string"
  _FREQUENCY = 1100
  _PLAY_DURATION = 80
  _LISTENING_TIME = 200  # seconds

  # pylint:disable=E1101
  def setUp(self):
    """
    Setup
    """
    self._debug = True  # Enable/disable debugging information

    self.network_delay_value_min = 0
    self.network_delay_value_max = 0

    # it actually does not make sense to verify versions on all DUTs,
    # as ED has already verified that they are the same
    if ASEHelpers.is_version_1_1(self.leader.tal) or ASEHelpers.is_version_1_0(self.leader.tal):
      self.skipTest("Invalid Software version of one of the DUT")

    self._element = ase_const.SOUND
    self._status_name = ase_const.STATUS
    self._general_name = ase_const.GENERAL
    self._setup_dut(self.leader)
    self._setup_dut(self.follower)

    # setup- follower1
    if hasattr(self, 'follower1'):
      self._setup_dut(self.follower1)

    self._leader_webpage_setup()

    self.setUp_done()

  def tearDown(self):
    """
    Tear down
    """
    self.tearDown_starts()

    self._teardown_dut(self.leader)
    self._teardown_dut(self.follower)

    if self.leader.bt_sound_card:
      res = self.leader.bt_sound_card.stop()
      self.logger.info("stopping leader bt_sound_card. Result: %s" % res)
      # disconnect bt device
      self.leader.bt_sound_card.execute_command("bt-audio -d %s" % self.leader.tal.bluetooth_mac_address)
    # TearDown follower1
    if hasattr(self, 'follower1'):
      self._teardown_dut(self.follower1)

  def _setup_dut(self, product):
    """ it sets up a device under test
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    if product == self.leader:
      product.name = "Leader"
    elif product == self.follower:
      product.name = "Follower"
    elif product == self.follower1:
      product.name = "Follower_1"
    else:
      product.name = "Unknown"
    self.logger.info("Setting up %s" % product.name)
    product.tal_http.debug = True
    if product.apple_communicator is not None:
      product.apple_communicator.ip_address = product.tal.get_ip()
      product.apple_communicator.create_client(60)

    product.sound_verification = ASEHelpers.SoundVerification(self.logger,
                                                              product.sound_card,
                                                              product.tal_http,
                                                              self.assertFalse,
                                                              self.assertEqual, 50)

    ASEHelpers.check_tunein_url(product.tal, product.tal_http, product.selenium_server, product.chromecast, self.skipTest)

    self._deezer_account = ASEHelpers.get_deezer_account(product.tal)
    self._tunein_account = comm_const.TUNEIN_ACCOUNT

    product.deezer_client = ASEHelpers.DeezerClientHelper(product.tal_http, self.logger, self._deezer_account, self.skipTest)
    product.tunein_client = ASEHelpers.TuneInClientHelper(product.tal_http, self.logger, self._tunein_account, self.skipTest, product.tal)

    product.dlna_client = ASEHelpers.DLNAClientHelper(product.tal_http, self.logger)
    product.verification = ASEHelpers.Verification(self.logger,
                                                   product.tal_http,
                                                   self.assertFalse,
                                                   self.assertEqual)
    product._power_state = ASEHelpers.PowerStateHelper(product.tal_http, self.logger)

    product._play_queue = PlayBack.PlayQueue(product.tal_http, self.logger)
    product._streaming = PlayBack.StreamingCommands(product.tal_http, self.logger)

    Helpers.clear_queue(product.tal_http)
    if product.sound_card:
      Helpers.mute_sound_output(product.sound_card)

  def _teardown_dut(self, product):
    """ it tears down a device under test
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Tearing down %s" % product.name)
    product.tal_http.send_http_command_delete(comm_const.BEOZONE_PRIMARY_EXPERIENCE)
    self.logger.info("stopping the stream")
    product._streaming.stop()
    if product.sound_card:
      Helpers.mute_sound_output(product.sound_card)
      res = product.sound_card.stop()
      self.logger.info("stopping sound_card. Result: %s" % res)

    if product.selenium_server:
      if hasattr(product, 'webpage'):
        product.webpage.driver.quit()
    # stop listening to notifications
    if product.tal_http.is_listening_to_notifications():
      product.tal_http.stop_listening_to_notifications()


  def _play_dlna(self, product):
    """This method will start playing DLNA on Leader/Followers and verify the current source
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Playing DLNA on %s" % product.name)
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    product.dlna_client.play_track(product.dlna_server.URL_DLNA, 10)
    product.sound_verification.verify_frequency(product.dlna_server.URL_FREQ_DLNA1[1])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    product.verification.verify_active_source(comm_const.Source.MUSIC)

  def _play_bluetooth(self, product, play_duration):
    """ Bluetooth connection with ASE and start playing a track on ASE using bluetooth
    if the play duration is long, it can take time for xml rpc server to generate
    corresponding sine file.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param play_duration: Specifies a duration to play.
    @type play_duration: integer
    """
    self.logger.info("Playing Bluetooth on %s" % product.name)
    Helpers.unmute_sound_output(self.leader.sound_card)
    self.logger.info("connecting to DUT")
    product.bt_sound_card.execute_command("bt-audio -c %s" % product.tal.bluetooth_mac_address)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.logger.info("Start playing bluetooth")
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.BLUETOOTH)
    play_result = product.bt_sound_card.play_frequency(self._FREQUENCY, play_duration)
    self.logger.info("Result from play_frequency: playing, message, duration, start_time: '%s'" % str(play_result))
    product.verification.verify_active_source(comm_const.Source.BLUETOOTH)

  def _play_linein_source(self, product):
    """Play and verifying the active source : Linein
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Playing line-in on %s" % product.name)
    Helpers.unmute_sound_output(self.leader.sound_card)
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.LINEIN)
    product.sound_card.play_frequency(self._FREQUENCY, self._PLAY_DURATION)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    product.sound_verification.verify_frequency(self._FREQUENCY)
    product.verification.verify_active_source(comm_const.Source.LINEIN)

  def _verify_active_source_playback(self, product1, product2, join_disable=False):
    """This method will compare two products currently active source, to check whether they are in joined session or not.
    @param product1: Leader/Follower
    @type product1: String
    @param product2: Leader/Follower
    @type product2: String
    If join_disable = true, Verify that follower should not join the leader
    If join_disable = false, Verify that follower should join the leader
    By default value is false for join_disable
    """
    self.logger.info("Verifying active source on %s and %s" % (product1.name, product2.name))
    # To find the jid of source on Leader
    res = product1.tal_http.send_http_command_get(comm_const.BEODEVICE_PRIMARYSOURCE)
    active_source_on_product1 = res[u'primaryExperience'][u'source'][u'id']
    # To find the jid of source on follower
    res_1 = product2.tal_http.send_http_command_get(comm_const.BEODEVICE_PRIMARYSOURCE)
    active_source_on_product2 = res_1[u'primaryExperience'][u'source'][u'id']
    # To verify that the source on both the product are same or not
    self.logger.info("primary source of leader = %s" % active_source_on_product1)
    self.logger.info("primary source of follower= %s" % active_source_on_product2)
    if join_disable:
      self.assertNotEqual(active_source_on_product1, active_source_on_product2, "Join is disabled yet Follower joined leader")
    else:
      self.assertEqual(active_source_on_product1, active_source_on_product2, "source not changed")

  def _join(self, product):
    """ Sending join command to product
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Sending join command to %s" % product.name)
    product.tal_http.send_http_command_post(comm_const.BEO_ONE_WAY_JOIN, '{"toBeReleased": true}')
    product.tal_http.send_http_command_post(comm_const.BEO_ONE_WAY_JOIN_RELEASE, '')
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)

  def _expand(self, source, listener):
    """ Sending expand command
    @param source: Product whose experience to be expanded
    @type Source: String
    @param listener: product on which the experience to be expanded
    @type listener: String
    """
    self.logger.info("Expanding from: '%s' to: '%s'" % (source.name, listener.name))
    res = listener.tal_http.send_http_command_get(comm_const.BEOCONTENT)
    follower_jid = res[u'sources'][0][u'name']
    next_value = (follower_jid).split(':')[1]
    data = {"listener": {"jid": next_value}}
    self.logger.info(data)
    source.tal_http.send_http_command_post(comm_const.BEOZONE_PRIMARY_EXPERIENCE, data)

  def _play_tunein(self, product):
    """Playing tunein source Leader/Follower.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Playing TuneIn on %s" % product.name)
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
    play_ids = product.tunein_client.add_stations_to_play_queue(1)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    product._play_queue.play_id_set(play_ids[0])

  def _play_join_verify_tunein(self):
    """This method will play tunein source on leader and send join command to follower. Then verifies whether follower has joined the leader or not using BNR
    """
    self.logger.info("Playing TuneIn on %s and join %s" % (self.leader.name, self.follower.name))
    self._play_tunein(self.leader)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)

  def _play_expand_verify_tunein(self, product1, product2):
    """This method will play tunein source on leader and send expand command to follower. Then verifies whether leader's source has expanded to the follower or not using BNR
    @param product1: leader
    @param product2: follower
    """
    self._play_tunein(product1)
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    self._expand(product1, product2)
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower)

  def _play_deezer(self, product):
    """Playing deezer source on Leader/Follower.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Playing Deezer on %s" % product.name)
    if not product.deezer_client.is_logged_in():
      product.deezer_client.logout()
      product.deezer_client.login()
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    play_ids = product.deezer_client.add_tracks_to_play_queue(1)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    product._play_queue.play_id_set(play_ids[0])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    play_now_track_id = product.tal_http.get_play_queue_playnowid()
    self.assertEqual(play_ids[0], play_now_track_id, "Track did not start playing")

  def _volume_increase(self, product, volume=10):
    """Volume -increase at Leader/Follower and verification using BNR
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param volume: level of volume to be increased
    @type volume: unsigned integer
    @return: speaker volume level of DUT after volume increased, using BNR
    @rtype: unsigned integer
    """
    self.logger.info("Volume increase on %s" % product.name)
    volume_level_bnr = product.tal_http.get_sound_volume_level()
    volume_level_increase = volume_level_bnr + volume
    self.logger.info(("volume_level_increase on product := % d") % volume_level_increase)
    ASEHelpers.set_sound_volume_level(product.tal_http, volume_level_increase)
    volume_level_bnr_after_increase = product.tal_http.get_sound_volume_level()
    return volume_level_bnr_after_increase

  def _volume_decrease(self, product, volume=10):
    """Volume decrease at Leader/Follower and verification using BNR
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param volume: level of volume to be decreased
    @type volume: integer
    @return: Speaker volume level of DUT after volume decreased, using BNR
    @rtype: integer
    """
    self.logger.info("Volume decrease on %s" % product.name)
    volume_level_bnr = product.tal_http.get_sound_volume_level()
    volume_level_decrease = volume_level_bnr - volume
    ASEHelpers.set_sound_volume_level(product.tal_http, volume_level_decrease)
    volume_level_bnr_after_decrease = product.tal_http.get_sound_volume_level()
    return volume_level_bnr_after_decrease

  def _verify_volume_after_change(self, product, volume_before_change):
    """Verifying change in volume on Leader/Follower and verification using BNR
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param volume_before_change: Expected volume before change.
    @type volume_before_change: integer
    """
    self.logger.info("Verifying volume change on %s" % product.name)
    volume_after_change = product.tal_http.get_sound_volume_level()
    self.logger.info(("Volume:=%d") % volume_after_change)
    self.assertEqual(volume_before_change, volume_after_change, "Volume is not same")

  def _verify_no_sound_from_speaker(self, product):
    """This method will verify that no sound is coming from speaker when speakers are muted.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Verifying no sound on %s" % product.name)
    channel = 2
    rec_channel = 1
    current_volume = product.sound_card.is_sound(channel, rec_channel)
    self.logger.info("current sound volume: %s" % current_volume)
    self.assertFalse(current_volume["result"], "Not passed - volume is not mute")

  def _standby(self, product, all_standby=False):
    """ Sending Standby command on product- Leader/Follower and verify their power states
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param all_standby: If true all standby will be sent.
    @type all_standby: boolean
    @return: actual power state of the product on which stand-by command has sent
    @rtype: string
    """
    self.logger.info("Sending standby to %s" % product.name)
    if all_standby:
      product.tal_http.send_http_command_put(comm_const.POWER_MANAGEMENT_STANDBY_MODIFY, {"standby": {"powerState": "allStandby"}})
    else:
      product.tal_http.power_state_standby_standby()
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    product.verification.verify_no_playback(product.sound_verification)
    actual_res = product.tal_http.get_power_state()
    return actual_res

  def _add_tracks_to_play_queue_dlna(self, count):
    """Fetch tracks from track list and then adding to play queue
    @param count: an amount of items to add
    @type count: integer
    @return: play_ids
    @rtype: string
    """
    self.logger.info("Adding DLNA tracks to %s" % self.leader.name)
    play_ids = []
    for i in range(count):
      tracks = self.leader.dlna_server.tracklist_arr[i]
      trk = json.dumps(tracks)
      data = '{"playQueueItem":[{"behaviour":"planned","track":%s}]}' % trk
      res = self.leader.tal_http.send_http_command_post(comm_const.BEOZONE_PLAYQUEUE, data)
      play_id = res["playQueue"]["playQueueItem"][0]["id"]
      play_ids.append(play_id)
    return play_ids

  def _verify_playqueue(self, product, is_empty):
    """ Verifying the tracks of leader/follower in the Playqueue using BNR
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param is_empty: check whether playqueue should be empty or not for the product
    @type is_empty: Boolean
    """
    self.logger.info("Verifying play queue on %s" % product.name)
    empty_playqueue = 0
    res = product.tal_http.send_http_command_get(comm_const.BEOZONE_PLAYQUEUE)
    playqueue_count = res["playQueue"]["total"]
    if is_empty:
      self.assertEqual(empty_playqueue, playqueue_count, "playqueue is not empty")
    else:
      self.assertNotEqual(empty_playqueue, playqueue_count, "playqueue is empty")

  def _follower_webpage_setup(self):
    """Setup for follower webpage
    """
    self.logger.info("Setup web page on %s" % self.follower.name)
    if hasattr(self, 'router_wlan') or hasattr(self, 'router_lan'):
      self.follower.selenium_server.ip_address = self.follower.tal.ip_address

    if self.follower.selenium_server:
      self.follower.webpage = webpage_get(self.follower.tal, self.follower.selenium_server)

      if self.follower.webpage:
        first_time_setup_level = self.follower.webpage.detect_first_time_setup()
        self.logger.info("First time setup level: %s" % first_time_setup_level)
        if first_time_setup_level:
          self.follower.webpage.run_first_time_setup(self.follower.chromecast, first_time_setup_level, True, True)
      else:
        self.skip_test("Web page not found! Skipping test")
    else:
      self.skip_test("Selenium_server not supported. Skipping test")

  def _leader_webpage_setup(self):
    """Setup for leader webpage
    """
    self.logger.info("Setup web page on %s" % self.leader.name)
    if hasattr(self, 'router_wlan') or hasattr(self, 'router_lan'):
      self.leader.selenium_server.ip_address = self.leader.tal.ip_address

    if self.leader.selenium_server:
      self.leader.webpage = webpage_get(self.leader.tal, self.leader.selenium_server)

      if self.leader.webpage:
        first_time_setup_level = self.leader.webpage.detect_first_time_setup()
        self.logger.info("First time setup level: %s" % first_time_setup_level)
        if first_time_setup_level:
          self.leader.webpage.run_first_time_setup(self.leader.chromecast, first_time_setup_level, True, True)
      else:
        self.skip_test("Web page not found! Skipping test")
    else:
      self.skip_test("Selenium_server not supported. Skipping test")

  def _sound_synchronization_set(self, connection, value):
    """ Set the wired network delay value
    @param value: integer value
    @param connection: Sound Synchronization in wired/wifi connection
    """
    self.logger.info("Setting %s sound synchronization value for %s" % (connection, self.leader.name))
    self._webpage_beolink(self.leader)
    self.leader.webpage.menu_click(ase_const.SOUND_SYNCHRONIZATION)
    self.leader.webpage.switch_to_right_frame()
    value_string = str(value)
    self.leader.webpage.text_box_fill(connection, value_string)
    if self.leader.webpage.button_click(ase_const.BUTTON_SOUND_SYNCHRONIZATION_CHANGE):
      self.leader.webpage.popup_menu_get()
      self.leader.webpage.button_click(ase_const.BUTTON_CONFIRM)

  def _sound_synchronization_values_get(self, connection):
    """To get minimum and maximum value of sound synchronization using BNR
    @param connection: wired/wireless
    """
    self.logger.info("Getting %s sound synchronization values for %s" % (connection, self.leader.name))
    network_delay_value = self.leader.tal_http.send_http_command_get(comm_const.BEOSETTING)
    self.network_delay_value_min = network_delay_value[u'settings'][u'networkDelay'][u'_capabilities'][u'range'][u'%s' % connection][0][u'min']
    self.network_delay_value_max = network_delay_value[u'settings'][u'networkDelay'][u'_capabilities'][u'range'][u'%s' % connection][0][u'max']

  def _sound_synchronization_verify(self, product, expected_value, connection, is_set_delay):
    """ Get values from BNR and verify the values of Sound Synchronization
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param expected_value: Verify to set values in Sound synchronization using BNR
    @type expected_value: Integer
    @param connection: wired/wireless
    @type connection: String
    @param is_set_delay: Verify whether the delay can be set or not
    @type is_set_delay: Boolean
    """
    self.logger.info("Verifying sound synchronization value for %s" % product.name)
    timeout = 2
    ASEHelpers.test_timeout(self.logger, timeout)
    res = product.tal_http.send_http_command_get(comm_const.BEOSETTING)
    network_delay = res[u'settings'][u'networkDelay'][u'%s' % connection]
    self.logger.info("Sound synchronization value found: %s" % network_delay)
    if is_set_delay:
      self.assertEqual(network_delay, expected_value, "Value is wrong. Found: %s Expected: %s" % (network_delay, expected_value))
    else:
      self.assertNotEqual(network_delay, expected_value, "Value was unexpectedly set! Found: %s" % network_delay)

  def _sound_synchronization_set_and_verify(self, connectivity, set_value, connection, is_set_delay=True):
    """ To set the Sound Synchronization value and verify using BNR
    @param connectivity: Connection Type- Wired/Wireless
    @type connectivity: String
    @param set_value: Sound Synchronization value to be set
    @type set_value: Integer/String
    @param connection: connection type wired/wireless
    @type connection: String
    @param is_set_delay: Verify whether the delay can be set or not
    @type is_set_delay: Boolean
    """
    self.logger.info("Set and verify sound synchronization value: %s" % set_value)
    self._sound_synchronization_set(connectivity, set_value)
    self._sound_synchronization_verify(self.leader, set_value, connection, is_set_delay)
    self._sound_synchronization_verify(self.follower, set_value, connection, is_set_delay)

  def _webpage_beolink(self, product):
    """To open beolink tab on webpage
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Activating BEOLINK menu on %s" % product.name)
    product.webpage.switch_to_left_frame()
    product.webpage.menu_click(ase_const.SETTINGS)
    product.webpage.menu_click(ase_const.BEOLINK)

  def _follower_navigate_to_join_menu(self):
    """To navigate to right frame in join tab on webpage
    """
    self.logger.info("Activating JOIN menu on %s" % self.follower.name)
    self._webpage_beolink(self.follower)
    self.follower.webpage.menu_click(ase_const.JOINSETUP)
    self.follower.webpage.switch_to_right_frame()

  def _sound_synchronization_delay_reset(self, connectivity):
    """To navigate to right frame in sound settings and activate reset.

    @param connectivity: Connection Type- Wired/Wireless
    @type connectivity: String
    """
    self.logger.info("Resetting sound synchronization delay on %s" % self.leader.name)
    self._webpage_beolink(self.leader)
    self.leader.webpage.menu_click(ase_const.SOUND_SYNCHRONIZATION)
    self.leader.webpage.switch_to_right_frame()
    self.leader.webpage.text_box_fill(connectivity, "1234")
    if self.leader.webpage.button_click(ase_const.BUTTON_SOUND_SYNCHRONIZATION_RESET):
      self.leader.webpage.popup_menu_get()
      self.leader.webpage.button_click(ase_const.BUTTON_CONFIRM)

  def _follower_join_uncheck(self):
    """To uncheck the checkbox for "Allows you to join a multi-room experience"
    """
    self.logger.info("Disabling multi-room join for %s" % self.follower.name)
    if self.follower.webpage.check_box_click("Enabled", False):
      self.follower.webpage.popup_menu_get()
      self.follower.webpage.button_click(ase_const.BUTTON_CONFIRM)
    self.follower.webpage.refresh()

  def _follower_join_check(self):
    """ To check the checkbox for "Allows you to join a multi-room experience"
    """
    self.logger.info("Enabling multi-room join for %s" % self.follower.name)
    if self.follower.webpage.check_box_click("Enabled", True):
      self.follower.webpage.popup_menu_get()
      self.follower.webpage.button_click(ase_const.BUTTON_CONFIRM)
    self.follower.webpage.refresh()

  def _follower_join_disable(self):
    """To disable "Allows you to join a multi-room experience"
    """
    self.logger.info("Disabling multi-room join for %s" % self.follower.name)
    self._follower_webpage_setup()
    self._follower_navigate_to_join_menu()
    self._follower_join_uncheck()

  def _follower_join_enable(self):
    """To enable "Allows you to join a multi-room experience"
    """
    self.logger.info("Enabling multi-room join for %s" % self.follower.name)
    self._follower_webpage_setup()
    self._follower_navigate_to_join_menu()
    self._follower_join_check()

  def _start_playing_itunes(self, product):
    """ Start playing iTunes in mac
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @return: the frequency of the playing track
    @rtype: integer

    @todo: don't forget to stop iTunes after sound verifications
    """
    self.logger.info("Playing iTunes on %s" % product.name)
    product_friendly_name = product.tal_http.get_product_friendly_name()
    self.logger.info("iTunes initiated on source")
    hres = product.apple_communicator.execute_apple_script('%s "%s"' % (product.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                                        product_friendly_name))
    self.logger.info("the apple script '%s' returns %s" % (product.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                           hres))
    if hres != ['0']:
      raise AssertionError("Cannot selecting speakers")
    product.apple_communicator.itunes_set_volume(50)
    product.apple_communicator.itunes_start_play_music()
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    playstate = product.apple_communicator.itunes_get_play_state()
    self.logger.info("iTunes play state is %s" % playstate)
    if ITunesState.PLAYING != playstate:
      raise AssertionError("iTunes is not playing")

  def _leader_verify_playing_status(self, playing_status):
    """This method will capture the notifications and verify the play/pause of leader
    @param: playing_status: play/pause
    @type: playing_status: string
    """
    self.logger.info("Verifying playing status on leader.")
    notifications_leader = self.leader.tal_http.get_notifications(50)

    self.logger.info("")
    self.logger.info("Verifying notifications on the leader.")
    self.logger.info("")
    correct_notification_leader = False
    if len(notifications_leader) < 1:
      self.logger.error("No notifications received from leader!")
    for notification in notifications_leader:
      if self._debug:
        self.logger.debug(notification)
      if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None).lower() == playing_status.lower():
        correct_notification_leader = True
    ASEHelpers.verify_notification_received(self.logger, correct_notification_leader, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', playing_status.lower())

  def _follower_verify_playing_status(self, playing_status):
    """This method will capture the notifications and verify the play/pause of follower
    @param: playing_status: play/pause
    @type: playing_status: string
    """
    self.logger.info("Verifying playing status on follower.")
    notifications_follower = self.follower.tal_http.get_notifications(50)

    self.logger.info("")
    self.logger.info("Verifying notifications on the follower.")
    self.logger.info("")
    correct_notification_follower = False
    if len(notifications_follower) < 1:
      self.logger.error("No notifications received from follower!")
    for notification in notifications_follower:
      if self._debug:
        self.logger.debug(notification)
      if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None).lower() == playing_status.lower():
        correct_notification_follower = True
    ASEHelpers.verify_notification_received(self.logger, correct_notification_follower, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', playing_status.lower())

  def _automatic_software_update_check(self):
    """To check the checkbox for enabling automatic software updates settings
    """
    self.logger.info("Enable automatic software update on %s" % self.leader.name)
    self.leader.webpage.switch_to_left_frame()
    self.leader.webpage.menu_click(ase_const.SOFTWARE_UPDATE)
    self.leader.webpage.switch_to_right_frame()
    self._leader_automatic_softwareupdate_check()
    self.leader.webpage.driver.switch_to.default_content()
    timeout = 3
    ASEHelpers.test_timeout(self.logger, timeout)
    self.logger.info("Automatic software update is now enabled")

  def _leader_automatic_softwareupdate_check(self):
    """ To check the checkbox for "Automatic system software update"
    """
    self.logger.info("Enabling Automatic system software update for %s" % self.leader.name)
    if self.leader.webpage.check_box_click("AutoSWU", True):
      self.leader.webpage.popup_menu_get()
      self.leader.webpage.button_click(ase_const.BUTTON_CONFIRM)
    self.leader.webpage.refresh()

  def _upload_file_for_software_update(self, file_path):
    """ To upload firmware file for software update on DUT
    @param file_path:location for uploading firmware on DUT
    """
    self.logger.info("Starting downloading the build '%s'" % file_path)
    local_file_name = Helpers.download_file_from_ftp(os.path.join(self._ASE_SW_FTP, file_path), self.logger)
    self.logger.info("The build has been downloaded to the file '%s'" % local_file_name)
    self.leader.webpage.switch_to_left_frame()
    try:
      self.leader.webpage.menu_click(ase_const.SOFTWARE_UPDATE)
    except AssertionError:
      self.leader.webpage.menu_click(ase_const.NEW_SOFTWARE_AVAILABLE)
    timeout = 3
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.webpage.switch_to_right_frame()
    self.leader.webpage.button_click(ase_const.BUTTON_LOCAL_UPDATE)
    self.leader.webpage.switch_to_right_frame()
#     file_browser = self.leader.webpage.driver.find_element_by_css_selector('input[type="file"]')
    file_browser = self.leader.webpage.driver.find_element_by_id('datafile')
    if file_browser:
      file_browser.click()
#       file_browser.send_keys(local_file_name)


# This is not possible yet might be done via thrift
    self.leader.webpage.driver.switch_to.window("open file")
    self.leader.webpage.text_box_fill(ase_const.BUTTON_BROWSE, local_file_name)
    self.leader.webpage.button_click(ase_const.BUTTON_LOAD_FILE)
    timeout = 180
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.webpage.switch_to_right_frame()
    self.leader.webpage.button_click(ase_const.BUTTON_LOCAL_UPDATE_CONFIRM)
    timeout = 500
    ASEHelpers.test_timeout(self.logger, timeout)
    try:
#       self._driver.find_element_by_xpath("//div[@class='Bo-input-section']")
      self._webpage.button_click(ase_const.BUTTON_LOCAL_UPDATE_DONE)
    except NoSuchElementException:
      self.logger.info("Software Update unsuccessful")

  def _verify_and_play_link_source(self, source_name, product):
    """ Play any link source on leader and verify playback status
    @param source_name: Link source name
    @type source_name: String
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    """
    self.logger.info("Playing link source on %s" % product.name)
    product_source_id = self._product_jid_get(product, False)
    self.logger.info("To verify that product is in play state or not")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    source_name_jid = source_name + ":" + product_source_id
    self.leader.tal_http.set_active_source(source_name_jid)
    self.logger.info("set link source on leader using BNR")
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader._streaming.play()
    self.logger.info("")
    self.logger.info("Verifying notifications on the leader.")
    self.logger.info("")
    notifications_leader = self.leader.tal_http.get_notifications(100)
    correct_notification = False
    for notification in notifications_leader:
      if self._debug:
        self.logger.debug(notification)
      if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None) == comm_const.PLAY_STATE:
        correct_notification = True
        break
    ASEHelpers.verify_notification_received(self.logger, correct_notification, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', comm_const.PLAY_STATE)
    self.logger.info("Verified link source is playing on leader")
    self.leader.tal_http.stop_listening_to_notifications()

  def _verify_mute_or_unmute(self, product, is_muted=True):
    """This method will verify if the source is muted or unmuted from the BNR
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param is_muted: to verify mute/unmute
    @type is_muted: Boolean
    """
    if is_muted:
      self.logger.info("Verifying if %s is muted" % product.name)
    else:
      self.logger.info("Verifying if %s is unmuted" % product.name)
    sound_state = product.tal_http.is_speaker_muted()
    if is_muted:
      self.logger.info("Expected mute state found: %s" % sound_state)
      self.assertTrue(sound_state, "DUT is still in unmuted state")
    else:
      self.logger.info("Expected mute state found: %s" % sound_state)
      self.assertFalse(sound_state, "DUT is still in muted state")

  def _product_jid_get(self, product, url_encoded=True):
    """ Gets the JID of specified product.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param url_encoded: Should the output jid be url encoded. (@ replaced by %40)
    @type url_encoded: boolean
    @return: jid of product
    """
    self.logger.info("Getting JID for %s" % product.name)
    product_jid = product.tal_http.product_id.primary_jid
    self.logger.info("The JID of product is: %s" % product_jid)
    if url_encoded:
      product_jid = product_jid.replace("@", "%40")
    return product_jid

  def _product_friendly_name(self, product):
    """ To find product friendly name of specified product.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @return product: Product friendly name
    """
    self.logger.info("Getting friendly name for %s" % product.name)
    product_name_bnr = product.tal_http.get_product_friendly_name()
    return product_name_bnr

  def _product_speaker_mute(self, product, delay=10):
    """ This will send a speaker mute command to specified product.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param delay: Specifies the delay before sound on output.
    @type delay: unsigned integer
    """
    self.logger.info("Sending speaker mute command to %s." % product.name)
    product.tal_http.speaker_mute()
    if delay > 0:
      self.logger.info("Waiting for no sound on output: %s seconds." % delay)
      time.sleep(delay)

  def _product_speaker_unmute(self, product, delay=10):
    """ This will send a speaker unmute command to specified product.
    @param product: Specifies the product to handle. E.g. self.leader or self.follower.
    @type product: String
    @param delay: Specifies the delay before sound on output.
    @type delay: unsigned integer
    """
    self.logger.info("Sending speaker unmute command to %s." % product.name)
    product.tal_http.speaker_unmute()
    if delay > 0:
      self.logger.info("Waiting for sound on output: %s seconds." % delay)
      time.sleep(delay)

  def _select_primary_product(self, product_jid, product_name_bnr):
    """ Select primary link product using web browser
    @param product_jid: product jid
    @type product_jid: String
    @param product_name_bnr: product friendly name
    @type product_name_bnr: String
    """
    self.logger.info("Selecting primary product: %s, jid: %s" % (product_name_bnr, product_jid))
    self.leader.webpage.switch_to_left_frame()
    self.leader.webpage.menu_click(ase_const.SETTINGS)
    self.leader.webpage.menu_click(ase_const.BEOLINK)
    self.leader.webpage.menu_click(ase_const.LINK_TO_OTHER_PRODUCTS)
    self.leader.webpage.switch_to_right_frame()
    if product_jid == "":
      self.leader.webpage.drop_down_menu_item_click(ase_const.DROPDOWN_PRIMARY_PRODUCT, product_jid)
#       self.leader.webpage.driver.find_element_by_xpath("//input[@type='submit' and @id='PrimaryButton']").click()
      self.leader.webpage.button_click(ase_const.BUTTON_PRIMARY)
    else:
      drop_down_text = self.leader.webpage.drop_down_menu_item_get(ase_const.DROPDOWN_PRIMARY_PRODUCT)
      if drop_down_text != product_name_bnr:
        self.leader.webpage.drop_down_menu_item_click(ase_const.DROPDOWN_PRIMARY_PRODUCT, product_jid)
#         self.leader.webpage.driver.find_element_by_xpath("//input[@type='submit' and @id='PrimaryButton']").click()
        self.leader.webpage.button_click(ase_const.BUTTON_PRIMARY)
    self.leader.webpage.driver.switch_to.default_content()

  def _select_secondary_product(self, product_jid, product_name_bnr):
    """ Select secondary link product using web browser
    @param product_jid: product jid
    @type product_jid: String
    @param product_name_bnr: product friendly name
    @type product_name_bnr: String
    """
    self.logger.info("Selecting secondary product: %s" % product_name_bnr)
    self.leader.webpage.switch_to_left_frame()
    self.leader.webpage.menu_click(ase_const.SETTINGS)
    self.leader.webpage.menu_click(ase_const.BEOLINK)
    self.leader.webpage.menu_click(ase_const.LINK_TO_OTHER_PRODUCTS)
    self.leader.webpage.switch_to_right_frame()
    if product_jid == "":
      self.leader.webpage.drop_down_menu_item_click(ase_const.DROPDOWN_SECONDARY_PRODUCT, product_jid)
      if self.leader.webpage.button_is_enabled(ase_const.BUTTON_SECONDARY):
        self.leader.webpage.button_click(ase_const.BUTTON_SECONDARY)
    else:
      drop_down_text = self.leader.webpage.drop_down_menu_item_get(ase_const.DROPDOWN_SECONDARY_PRODUCT)
      if drop_down_text != product_name_bnr:
        self.leader.webpage.drop_down_menu_item_click(ase_const.DROPDOWN_SECONDARY_PRODUCT, product_jid)
        if self.leader.webpage.button_is_enabled(ase_const.BUTTON_SECONDARY):
          self.leader.webpage.button_click(ase_const.BUTTON_SECONDARY)

  def beolink_volume_level(self):
    """ A local operation volume level is not sent to the sourcing product

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Volume up on Follower
      -> Volume on Follower has been increased
      -> Volume on Leader - no changes
      3. Volume down on Follower
      -> Volume on Follower has been decreased
      -> Volume on Leader - no changes

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    volume_before_change_leader = self.leader.tal_http.get_sound_volume_level()
    volume_level_bnr = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr_after_increase = self._volume_increase(self.follower)
    volume_difference = volume_level_bnr_after_increase - volume_level_bnr
    volume_diff = 10
    self.assertEqual(volume_difference, volume_diff, "volume is not increased as expected")
    self._verify_volume_after_change(self.leader, volume_before_change_leader)
    volume_level_bnr = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr_after_change = self._volume_decrease(self.follower)
    volume_difference = volume_level_bnr - volume_level_bnr_after_change
    self.assertEqual(volume_difference, volume_diff, "Volume level different")
    self._verify_volume_after_change(self.leader, volume_before_change_leader)

  def beolink_mute_unmute_follower(self):
    """ A local operation mute-umute is not sent to the sourcing product

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the Follower
      -> no sound from the Follower
      -> sound comes from the Leader
      3. Unmute the Follower
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self._product_speaker_mute(self.follower)
    self._verify_no_sound_from_speaker(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.logger.info("Follower is muted")
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self._product_speaker_unmute(self.follower)
    self.follower.sound_verification.verify_sound(True)
    self.leader.sound_verification.verify_sound(True)
    self.logger.info("Follower is unmuted")

  def beolink_mute_unmute_leader(self):
    """ A local operation mute-umute is not sent to the sinking product

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the Leader
      -> no sound from the Leader
      -> sound comes from the Follower
      3. Unmute the Leader
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.follower.sound_verification.verify_sound(True)
    self.leader.sound_verification.verify_sound(True)
    self._product_speaker_mute(self.leader)
    self.follower.sound_verification.verify_sound(True)
    self._verify_no_sound_from_speaker(self.leader)
    self._product_speaker_unmute(self.leader)
    self.follower.sound_verification.verify_sound(True)
    self.leader.sound_verification.verify_sound(True)
    self.logger.info("Leader is unmuted")

  def beolink_join_disable(self):
    """ A DUT Follower cannot join the playing Leader (DLNA)
    when join is turned off.

    Steps:
      1. Turn off Join functionality on the Follower (using the corresponding web page)
      2. Start playing on a Leader sound frequency M
      3. Try to join the Follower to the Leader
      -> the Follower cannot join the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_disable()
    self._play_dlna(self.leader)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower, join_disable=True)

  def beolink_play_join_dlna(self):
    """A DUT Follower can join the playing Leader (DLNA)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Join the Follower to the Leader
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_dlna(self.leader)
    self._join(self.follower)
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA1[1])
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_join_tunein(self):
    """ A DUT Follower can join the playing Leader (tunein)

    Steps:
      join is turned on
      1. Start playing on a  Leader using tunein
      2. Join the Follower to the Leader
      -> sound  comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_play_join_deezer(self):
    """ A DUT Follower can join the playing Leader (deezer)

    Steps:
      join is turned on
      1. Start playing on a  Leader using deezer
      2. Join the Follower to the Leader
      -> sound  comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_deezer(self.leader)
    self._join(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_join_bluetooth(self):
    """ A DUT Follower can join the playing Leader (bluetooth)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Join the Follower to the Leader
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_bluetooth(self.leader, self._PLAY_DURATION)
    self._join(self.follower)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_join_linein(self):
    """ A DUT Follower can join the playing Leader (linein)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Join the Follower to the Leader
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_linein_source(self.leader)
    self._join(self.follower)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_join_itunes(self):
    """ A DUT Follower cannot join the playing Leader (iTunes)

    Steps:
      join is turned on
      1. Start playing on a  Leader using iTunes
      2. Try to Join the Follower to the Leader
      -> it cannot join

     Hyperion::
      @Role1: Leader
      @Equipment1: [apple_communicator]
      @Role2: Follower
    """
    self._follower_join_enable()
    self._start_playing_itunes(self.leader)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower, join_disable=True)
    self.leader.apple_communicator.itunes_select_computer_speaker()
    self.leader.apple_communicator.itunes_stop()

  def beolink_play_expand_dlna(self):
    """ A DUT can expand playing from the Leader to the Follower (dlna)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Expend the Leader to the Follower
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_dlna(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_expand_tunein(self):
    """ A DUT can expand playing from the Leader to the Follower (tunein)

    Steps:
      join is turned on
      1. Start playing on a  Leader
      2. Expend the Leader to the Follower
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_join_verify_tunein()
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_expand_deezer(self):
    """ A DUT can expand playing from the Leader to the Follower (deezer)

    Steps:
      join is turned on
      1. Start playing on a  Leader
      2. Expand the Leader to the Follower
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_deezer(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_expand_bluetooth(self):
    """ A DUT can expand playing from the Leader to the Follower (bluetooth)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Expend the Leader to the Follower
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_bluetooth(self.leader, self._PLAY_DURATION)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_expand_linein(self):
    """ A DUT can expand playing from the Leader to the Follower (line in)

    Steps:
      join is turned on
      1. Start playing on a  Leader sound frequency M
      2. Expend the Leader to the Follower
      -> sound frequency M comes from the Follower
      -> sound  frequency M comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._follower_join_enable()
    self._play_linein_source(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_expand_itunes(self):
    """ A DUT cannot expand playing from the Leader to the Follower (iTunes)

    Steps:
      join is turned on
      1. Start playing on a  Leader using iTunes
      2. Try to expend the Leader to the Follower
      -> it cannot expand

     Hyperion::
      @Role1: Leader
      @Equipment1: [apple_communicator]
      @Role2: Follower
    """
    self._follower_join_enable()
    self._start_playing_itunes(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower, join_disable=True)
    self.leader.apple_communicator.itunes_select_computer_speaker()
    self.leader.apple_communicator.itunes_stop()

  def beolink_playback_next_previous(self):
    """ A playback (next-previous) is controlled from the follower

    Steps:
      1. Add 2 dlna tracks to a playqueue on the Leader
      2. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct
      -> play queue is empty on the Follower
      -> play queue is not empty on the Leader
      3. Send the command 'Next' to the Follower
      -> the Leader starts playing the next track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader
      4. Send the command 'Previous' to the Follower
      -> the Leader starts playing the previous track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    play_ids = self._add_tracks_to_play_queue_dlna(2)
    self.leader._play_queue.play_id_set(play_ids[0])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._join(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)
    self._verify_playqueue(self.leader, False)
    self._verify_playqueue(self.follower, True)
    self.logger.info("Sending next command to Follower")
    next_id = self.leader._play_queue.play_id_calculate(1)
    self.follower._streaming.forward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(next_id, play_now_id, "Next track did not start playing")
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.logger.info("Sending previous command to Follower")
    prev_id = self.leader._play_queue.play_id_calculate(-1)
    self.follower._streaming.backward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(prev_id, play_now_id, "Previous track did not start playing")

  def beolink_playback_pause_play(self):
    """ A playback (pause-play) is controlled from the follower

    Steps:
      1. Start dlna playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'
      2. Send the command 'Pause' to the Follower
      -> no sound from the Follower
      -> not sound from the Leader
      -> playback status is 'pause'
      3. Send the command 'Play' to the Follower
      -> the Leader starts playing
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self._play_dlna(self.leader)
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    self._join(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.follower._streaming.pause()
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PAUSE_STATE)
    self.follower._streaming.play()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_leader_change_leader(self):
    """ The sink goes through all changes of sources along with the Leader

    Steps:
      1. Start playing dlna from a Beolink Leader (join) with the sound frequency M
      -> sound freq. M comes from the Follower
      -> sound freq. M comes from the Leader
      2. On the Leader switch to line in, start playing sound frequency N
      -> sound freq. N comes from the Follower
      -> sound freq. N comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_dlna(self.leader)
    self._join(self.follower)
    self.leader.sound_verification.verify_frequency(self.leader.dlna_server.URL_FREQ_DLNA1[1])
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA1[1])
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.tal_http.set_active_source(comm_const.SourceJidPrefix.LINEIN)
    self._play_linein_source(self.leader)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_leader_change_follower(self):
    """ The sink stops playing from the source if the sink selects a local source

    Steps:
      1. Start playing dlna from a Beolink Leader (join) with the sound frequency M
      -> sound freq. M comes from the Follower
      -> sound freq. M comes from the Leader
      2. On the Follower switch to dlna, play sound frequency N
      -> sound freq. N comes from the Follower
      -> sound freq. M comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_dlna(self.leader)
    self._join(self.follower)
    self.leader.sound_verification.verify_frequency(self.leader.dlna_server.URL_FREQ_DLNA1[1])
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA1[1])
    self._verify_active_source_playback(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._play_dlna(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_frequency(self.leader.dlna_server.URL_FREQ_DLNA1[1])
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA2[1])
    self.follower.verification.verify_active_source(comm_const.Source.MUSIC)
    self._verify_active_source_playback(self.leader, self.follower, join_disable=True)

  def beolink_standby_leader(self):
    """ The Leader goes to standby, but continues playing on the Follower

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'Standby' to the Leader
      -> no sound from the Leader
      -> sound comes from the Follower

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._standby(self.leader)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_standby_follower(self):
    """ The Follower goes to standby, but Leader continues playing

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'Standby' to the Follower
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.verification.verify_playback(self.leader.sound_verification)
    self.follower.verification.verify_playback(self.follower.sound_verification)

    power_status_follower = self._standby(self.follower)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.verification.verify_playback(self.leader.sound_verification)
    self.follower.verification.verify_no_playback(self.follower.sound_verification)

  def beolink_all_standby(self):
    """ Both the Follower and the Leader go to standby

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'AllStandby' to the Follower
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> no sound from the Leader
      -> power management's status on the Leader is 'standby

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    power_status_follower = self._standby(self.follower, all_standby=True)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    power_status_leader = self.leader.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_leader.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_all_standby_not_connected(self):
    """Both the Follower and the Leader go to standby even if they are not connected

    Steps:
      1. Start playing a local source from a Beolink Leader
      -> sound comes from the Leader
      2. Start playing a local source from a Beolink Follower
      -> sound comes from the Follower
      3. Send the command 'AllStandby' to the Follower
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> no sound from the Leader
      -> power management's status on the Leader is 'standby

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_tunein(self.leader)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_sound(True)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    self._play_dlna(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.follower.sound_verification.verify_sound(True)
    self.follower.verification.verify_active_source(comm_const.Source.MUSIC)
    power_status_follower = self._standby(self.follower, all_standby=True)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    power_status_leader = self.leader.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_leader.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_settings_discover(self):
    """ An ASE product can be discovered by another ASE product

    Steps:
      1. Discover one ASE product from another ASE product using BNR (/BeoZone/System/Products)
      -> the following info should be returned:
        - Product name (friendly name)
        - SW version
        - serial number
        - wired/wireless
        - type number
        - item number

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    res = self.follower.tal_http.send_http_command_get(comm_const.BEOCONTENT)
    jID = res[u'sources'][0][u'name']
    jid_prod = (jID).split(":")[1]
    self.logger.info(jid_prod)
    res1 = self.leader.tal_http.send_http_command_get(comm_const.BEOPRODUCT)
    jIds = res1[u'products']
    found_friendly_Name = ""
    for jId in jIds:
      if jId[u'jid'] == jid_prod:
        found_friendly_Name = jId[u'friendlyName']
        break
    self.logger.info("Product Friendly Name of other ASE Product %s" % found_friendly_Name)
    ser_no = (jid_prod).split("@")[0]
    type_no = (ser_no).split(".")[0]
    item_no = (ser_no).split(".")[1]
    serial_no = (ser_no).split(".")[2]
    self.logger.info("Type number: %s" % type_no)
    self.logger.info("Item number: %s" % item_no)
    self.logger.info("Serial number: %s" % serial_no)
    data = self.follower.tal_http.send_http_command_get(comm_const.BEODEVICE)
    typ = data[u'beoDevice'][u'productId'][u'typeNumber']
    self.assertEqual(type_no, typ, "Type number do not Match")
    item = data[u'beoDevice'][u'productId'][u'itemNumber']
    self.assertEqual(item_no, item, "Item number do not Match")
    serial = data[u'beoDevice'][u'productId'][u'serialNumber']
    self.assertEqual(serial_no, serial, "Serial number do not Match")
    sw_ver = data[u'beoDevice'][u'software'][u'version']
    self.logger.info("Software Version: %s" % sw_ver)
    network_set = self.follower.tal_http.send_http_command_get(comm_const.BEODEVICE_NETWORK_SETTINGS)
    status = network_set[u'profile'][u'networkSettings'][u'activeInterface']
    self.logger.info("Active Status of DUT: %s" % status)

  def beolink_webpage_discover(self):
    """Products found on your network

    Prerequisites:
      - there are 2 ASE products in the network
    Steps:
    1. Open Settings-Beolink-Discover Devices from one of DUT
    -> verify that the other DUT is shown here

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    res = self.follower.tal_http.send_http_command_get(comm_const.BEOCONTENT)
    jid = res[u'sources'][0][u'name']
    jid_prod = (jid).split(":")[1]
    self._webpage_beolink(self.leader)
    self.leader.webpage.menu_click(ase_const.DISCOVER)
    self.leader.webpage.switch_to_right_frame()
    self.leader.webpage.button_click(ase_const.BUTTON_REFRESH)
    product_name = self.leader.webpage.device_list_item_text_get("DevicesList", jid_prod)
    self.logger.info("Product Friendly Name : %s" % product_name)
    value = self.follower.tal_http.send_http_command_get(comm_const.BEODEVICE)
    product_name_bnr = value[u'beoDevice'][u'productFriendlyName'][u'productFriendlyName']
    self.assertEqual(product_name, product_name_bnr, "Product is Not available!")

  def beolink_webpage_network_delay_wired(self):
    """Sound sync settings can be changed
    The functionality behind the settings will be verified
    in the corresponding test for BNR

    Prerequisites:
      - there are 2 ASE products in the network

    Setup:
      get min, max from /BeoZone/System/Settings's capabilities

    Steps:
      1. Open Settings-Beolink-Join Setup from one of DUT
      2. Change settings for Network delay wired to
      - min-1
      - min
      - min+1
      - max
      - max + 1
      - string
      -> verify with BNR, that settings have been changed or not
      and check that it has changed on the other device in the network too

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._sound_synchronization_delay_reset(comm_const.WIREDDELAY)
    self._sound_synchronization_values_get(comm_const.CONNECTION_WIRED)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self.network_delay_value_min - 1, comm_const.CONNECTION_WIRED, False)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self.network_delay_value_min, comm_const.CONNECTION_WIRED, True)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self.network_delay_value_min + 1, comm_const.CONNECTION_WIRED, True)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self.network_delay_value_max, comm_const.CONNECTION_WIRED, True)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self.network_delay_value_max + 1, comm_const.CONNECTION_WIRED, False)
    self._sound_synchronization_set_and_verify(comm_const.WIREDDELAY, self._STRING, comm_const.CONNECTION_WIRED, False)

  def beolink_webpage_sound_network_delay_wifi(self):
    """Sound sync settings can be changed
    The functionality behind the settings will be verified
    in the corresponding test for BNR

    Prerequisites:
      - there are 2 ASE products in the network

    Setup:
      get min, max from /BeoZone/System/Settings's capabilities

    Steps:
      1. Open Settings-Beolink-Join Setup from one of DUT
      2. Change settings for Network delay wifi to
      - min-1
      - min
      - min+1
      - max
      - max + 1
      - string
      -> verify with BNR, that settings have been changed or not
      and check that it has changed on the other device in the network too

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._sound_synchronization_delay_reset(comm_const.WIFIDELAY)
    self._sound_synchronization_values_get(comm_const.CONNECTION_WIRELESS)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self.network_delay_value_min - 1, comm_const.CONNECTION_WIRELESS, False)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self.network_delay_value_min, comm_const.CONNECTION_WIRELESS, True)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self.network_delay_value_min + 1, comm_const.CONNECTION_WIRELESS, True)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self.network_delay_value_max, comm_const.CONNECTION_WIRELESS, True)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self.network_delay_value_max + 1, comm_const.CONNECTION_WIRELESS, False)
    self._sound_synchronization_set_and_verify(comm_const.WIFIDELAY, self._STRING, comm_const.CONNECTION_WIRELESS, False)

  def beolink_webpage_automatic_update_settings_broadcast(self):
    """when enabling or disabling automatic updates the setting
    must be broadcast to all other BeoLink products on the subnet,
    to force them into the same setting.

    Prerequisites:
      - there are 2 ASE products in the network
    Steps:
      1. Set the setting Automatic SW update to false for both 2 products
      2. Set the setting Automatic SW update to true for one of products
      -> verify that the setting Automatic SW update has been set true for the other product

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.logger.info("Disabling the automatic software update.")
    try:
      self.leader.tal_http.send_http_command_put(comm_const.SOFTWARE_UPDATE_MODE_MODIFY, {"mode": {"mode": comm_const.MODE_MANUAL}})
      timeout = 10
      ASEHelpers.test_timeout(self.logger, timeout)
      self.follower.tal_http.send_http_command_put(comm_const.SOFTWARE_UPDATE_MODE_MODIFY, {"mode": {"mode": comm_const.MODE_MANUAL}})
      timeout = 10
      ASEHelpers.test_timeout(self.logger, timeout)
      self.logger.info("Automatic software update is now disabled")
    except NoSuchElementException:
      self.logger.info("Checkbox is already unchecked")
    self._leader_webpage_setup()
    self._automatic_software_update_check()
    sfupdate_mode_leader = self.leader.tal_http.send_http_command_get(comm_const.SOFTWARE_UPDATE_MODE)
    sfupdate_mode_bnr_leader = sfupdate_mode_leader[u'profile'][u'softwareUpdate'][u'mode'][u'mode']
    self.assertEqual(comm_const.MODE_AUTOMATIC, sfupdate_mode_bnr_leader, "Automatic update software state is not set on leader")
    software_update_mode_follower = self.follower.tal_http.send_http_command_get(comm_const.SOFTWARE_UPDATE_MODE)
    sfupdate_mode_bnr_follower = software_update_mode_follower[u'profile'][u'softwareUpdate'][u'mode'][u'mode']
    self.assertEqual(comm_const.MODE_AUTOMATIC, sfupdate_mode_bnr_follower, "Automatic update software state is not broadcasted on follower")

  def beolink_join_after_standby(self):
    """ To verify that product can join after standby

    steps:
      1. Play different local sources on products (Not joined)
      2. Send high power standby to Product B (Follower)
      -> power management's status on the Follower is 'standby'
      -> Sound from product A
      3. Send join command to Product B
      -> Verify that the products are joined
      -> Sound comes from the Leader
      -> Sound comes from the Follower

      Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_dlna(self.leader)
    power_status_follower = self._standby(self.follower)
    timeout = 2
    ASEHelpers.test_timeout(self.logger, timeout)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_sound(True)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_change_source_on_leader_after_standby(self):
    """ To verify the source shange on leader after "distributing only" mode.

    steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send high power standby to Product A (Leader)
      -> power management's status on the Leader is 'standby'
      # Power status of leader doesn't go to 'standby' when it is in 'distributing only' mode. Cannot verify power state.
      -> No sound comes from the Leader
      -> Sound comes from the Follower
      3. Start playing DLNA source on Leader.
      -> Sound comes from the Leader
      -> Sound comes from the Follower
      -> Verify active source of Leader and Follower

      Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._standby(self.leader)
    timeout = 2
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_dlna(self.leader)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_play_bluetooth_on_follower_after_leader_lost_connection(self):
    """ To verify that follower plays bluetooth after leader lost connection

    steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Power off the Leader
      -> power management's status on the product B (Follower) is 'standby'
      4. Start playing bluetooth on Product B.
      -> Verify the source on the Product B
      -> Verify the sound from the Product B
      5. Power on the leader

      Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Equipment2: [bt_sound_card]
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    res = self.leader.tal.hard_reboot()
    if not res:
      raise AssertionError("BNR is not running")
    self._play_bluetooth(self.follower, self._PLAY_DURATION)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)

  def beolink_join_after_itunes(self):
    """ To verify that product joins after iTunes as a last played source

    steps:
      1. Play iTunes on Product B.
      -> Verify active source AIRPLAY
      2. start playing Deezer on Product A
      -> Verify active source DEEZER
      2. Send high power standby to Product B.
      -> Verify No sound from the Product B
      -> Sound comes from Product A
      3. Send join command to Product B.
      -> Verify that the products are joined
      -> Sound comes from the Leader.
      -> Sound comes from the Follower.

      Hyperion::
      @Role1: Leader
      @Equipment1: [apple_communicator]
      @Role2: Follower
    """
    self._play_tunein(self.leader)
    self._start_playing_itunes(self.follower)
    power_status_follower = self._standby(self.follower)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_no_sound(True)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self.follower.apple_communicator.itunes_select_computer_speaker()
    self.follower.apple_communicator.itunes_stop()

  def beolink_multiroom_session_for_longer_duration(self):
    """ To verify that multiroom session is running for longer duration

    Prerequisites:
      - Maximum playback timing should be 12 hours or 24 hours
    steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Play the multiroom session over night.
      -> sound comes from the Follower
      -> sound comes from the Leader

      Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    sleep_timeout = self._LONG_TIME
    ASEHelpers.test_timeout(self.logger, sleep_timeout, "Playing TuneIn for a long time.")
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_power_off_on_leader(self):
    """ To verify the joined experience when leader gets switched off during playback.

    Steps:
    1. Start playing from a Beolink Leader (join)
    -> sound comes from the Follower
    -> sound comes from the Leader
    2. Power off Leader
    -> Verify that they are not in joined session
    -> verify active source on Follower
    -> Verify the 'pause' on the Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    start_time = time.time()
    res = self.leader.tal.hard_reboot()
    if not res:
      raise AssertionError("BNR is not running")
#     sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
#     ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
    standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
    self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    power_status_follower = self.follower.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)

  def beolink_join_command_multiple_times_within_30sec(self):
    """ To verify if product keeps on joining multiple experiences on pressing sound button multiple times.

    Steps:
    1. Start playing Deezer source on Product B.
    2. Start playing from a Beolink Leader (join)
    -> sound comes from the Follower
    -> sound comes from the Leader
    3. Send join command to Follower
    -> sound comes from the product B (Follower)
    -> sound comes from the product A (Leader)
    -> Verify active source of product A (Leader) is as previous
    -> Verify active source on product B (Follower) is TuneIn.
    4. Send join command to product B(Follower) within 30 sec.
    -> Verify active source on product B is Deezer.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    raise NotImplementedError
    """
    self._play_tunein(self.leader)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self._play_deezer(self.follower)
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._join(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    res = self.follower.tal_http.send_http_command_get(comm_const.BEODEVICE_PRIMARYSOURCE)
    active_source_on_product = res[u'primaryExperience'][u'source'][u'id']
    print("active_source on follower_1st time: %s" % active_source_on_product)
    self.follower.verification.verify_active_source(comm_const.Source.RADIO)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    self._join(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    res = self.follower.tal_http.send_http_command_get(comm_const.BEODEVICE_PRIMARYSOURCE)
    active_source_on_product = res[u'primaryExperience'][u'source'][u'id']
    print("active_source on follower__2nd time : %s" % active_source_on_product)
    self._verify_active_source_playback(self.leader, self.follower)
    self.follower.verification.verify_active_source(comm_const.Source.DEEZER)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    """

  def beolink_join_command_multiple_times_after_30sec(self):
    """ To verify if CA6 keeps on joining multiple experiences on pressing sound button multiple times.

    Steps:
    1. Start playing from a Beolink Leader (join)
    -> sound comes from the Follower
    -> sound comes from the Leader
    2. Send join command to Follower
    -> sound comes from the product B (Follower)
    -> sound comes from the product A (Leader)
    -> Verify active source of product A (Leader) is as previous
    -> Verify active source on product B (Follower) is TuneIn.
    3 Send join command to product B after 30 second
    -> sound comes from the Follower
    -> sound comes from the Leader
    -> Verify that they are in join condition

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    raise NotImplementedError
    """
    self._play_deezer(self.follower)
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._join(self.follower)
    self.follower.verification.verify_active_source(comm_const.Source.RADIO)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    timeout = 30
    ASEHelpers.test_timeout(self.logger, timeout)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    """

  def beolink_leader_can_become_follower(self):
    """ To verify if leader can become the follower of other session

    Prerequisites:
      - there are 3 ASE products in the network
    Steps:
    1. Start playing from a Beolink Product A Leader (join)
    -> sound comes from the product B (Follower)
    -> sound comes from the product A (Leader)
    2. Start playing on a product C
    3. Send join command to product A
    -> Verify that product A and product C are in joined session
    -> sound comes from the product C
    -> sound comes from the product A
    -> verify active source of product C, product A should be same

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_deezer(self.follower1)
    self._join(self.leader)
    self._verify_active_source_playback(self.leader, self.follower1)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)

  def beolink_follower_can_become_follower_of_other_session(self):
    """ To verify if follower can become the follower of other session

    Prerequisites:
      - there are 3 ASE products in the network
    Steps:
    1. Start playing from a Beolink Product A Leader (join)
    -> sound comes from the product B (Follower)
    -> sound comes from the product A (Leader)
    2. Start playing on a product C
    3. Send join command to product B
    -> Verify that product B and product C are in joined session
    -> sound comes from the product C
    -> sound comes from the product B
    -> verify active source of product C, product B should be same

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_deezer(self.follower1)
    self._join(self.follower)
    self._verify_active_source_playback(self.follower, self.follower1)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)

  def beolink_join_when_no_ongoing_experience_available(self):
    """ To verify Join command for product A when no ongoing experience is available in the network.

    Prerequisites:
      - No playback on product A
    Steps:
    1. Send join command to product B
    -> sound comes from the product B
    -> verify active source of product B is TuneIn.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._standby(self.leader, True)
    self._join(self.follower)
    self.follower.sound_verification.verify_sound(True)
    self.follower.verification.verify_active_source(comm_const.Source.RADIO)

  def beolink_volume_on_leader_when_in_distributing_only_mode(self):
    """ Verify volume change on Leader when leader is in distributing only mode

    Steps:
    1. Start playing from a Beolink Leader (join)
    -> sound comes minutesfrom the Follower
    -> sound comes from the Leader
    2. Put leader into high power standby.
    -> No sound comes from the Leader
    -> Verify sound comes from Follower.
    3. Change the volume on Leader
    -> verify no change in volume on Leader
    -> verify no change in volume on Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Equipment: [sound_card]
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._standby(self.leader)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.follower.sound_verification.verify_sound(True)
    volume_level_bnr_before_change = self.leader.tal_http.get_sound_volume_level()
    self.logger.info("volume on leader before change: %s " % volume_level_bnr_before_change)
    self.leader.tal_http.speaker_continuous_down(1)
    volume_level_bnr_after_change = self.leader.tal_http.get_sound_volume_level()
    self.logger.info("volume on leader after change: %s " % volume_level_bnr_after_change)
    self.assertEqual(volume_level_bnr_before_change, volume_level_bnr_after_change, "Volume is not same")

  def beolink_expand_experience_when_leader_start_sw_updating(self):
    """ To verify the expanded experience when software update starts on leader

    Prerequisites:
      - there are 2 ASE products in the network
    Steps:
    1. Start playing from a Beolink Leader (expand)
    -> Verify that they are in joined session
    -> sound comes from the Follower
    -> sound comes from the Leader
    2. Initiate the software update on Leader.
    -> Verify playback status of Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_tunein(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)
    start_time = time.time()
    self._upload_file_for_software_update(ase_const.VALID_BUILD)
#     sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
#     ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
    standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
    self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    power_status_follower = self.follower.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)

  def beolink_expand_on_multiple_products(self):
    """ To verify Product can expand it's playback on multiple products

    Prerequisites:
      - there are 3 ASE products in the network
    Steps:
    1. Start playing on a  Leader
    2. Join the other products to the leader by join command.
    -> sound  comes from the Follower's
    -> sound comes from the Leader
    -> Verify that product A product B and product C are in joined session

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    self._play_dlna(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.MUSIC)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)
    self._expand(self.leader, self.follower)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower)
    self._expand(self.leader, self.follower1)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower1)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)

  # ASE-1.2
  def beolink_cyclic_timeout_of_30_seconds(self):
    """ To verify if first source in the list is selected when there has been no activity for 30 seconds, otherwise next source in the list should be selected.

    Prerequisites:
      - There are 3 products A,B,C in the network.

    Steps:
    1. Start playing in each product
    2. Send join command to product B.
    -> verify if product join the experience from "A" product in the network.
    3. Send the join command again.
    -> verify if product join the experienced from another product "C" in the network.
    4. Send the join command to product B within 30 seconds.
    -> verify if product join the first source in the source list.
    5. Send the join command again after 30 seconds.
    -> verify if product join the experience from other product in the network, that could be "A" or "C".

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    raise NotImplementedError
    """
    self._play_join_verify_tunein()
    self._play_dlna(self.follower1)
    self._join(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.follower, self.follower1)
    self._join(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.follower, self.leader)
    self.follower.verification.verify_active_source(comm_const.Source.RADIO)
    self._join(self.follower)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.follower, self.follower1)
    """

  def beolink_verify_dlna_can_interrupt_multiroom_experience(self):
    """ Verify if DLNA source playback interrupt playback from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing DLNA source on Leader
      -> Verify active source of Leader and Follower should be DLNA
      -> sound comes from the Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_dlna(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.MUSIC)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_verify_deezer_can_interrupt_multiroom_experience(self):
    """ Verify that Deezer playback interrupts playback from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing Deezer source on Leader
      -> Verify active source of Leader and Follower should be Deezer
      -> sound comes from the Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_deezer(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.DEEZER)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_verify_tunein_can_interrupt_multiroom_experience(self):
    """ Verify that TuneIn playback interrupts playback from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing TuneIn source on Leader
      -> Verify active source of Leader and Follower should be TuneIn
      -> sound comes from the Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_deezer(self.leader)
    self._join(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_tunein(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_verify_linein_can_interrupt_multiroom_experience(self):
    """ Verify that LineIn playback interrupts playback from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing LineIn source on Leader
      -> Verify active source of Leader and Follower should be LineIn
      -> sound comes from the Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_linein_source(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.LINEIN)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_verify_bluetooth_can_interrupt_multiroom_experience(self):
    """ Verify that Bluetooth playback interrupts playback from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing Bluetooth source on Leader
      -> Verify active source of Leader and Follower should be Bluetooth
      -> sound comes from the Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_bluetooth(self.leader, self._PLAY_DURATION)
    self.leader.verification.verify_active_source(comm_const.Source.BLUETOOTH)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_verify_airPlay_can_interrupt_multiroom_experience(self):
    """ Verify if AirPlay interrupts when playback on CA6 is active from joined/expanded experience

    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Start playing Airplay source on Leader
      -> Verify active source of Leader and Follower should be Airplay
      -> No sound comes from Follower
      -> sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Equipment1: [apple_communicator]
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._start_playing_itunes(self.leader)
    self.leader.verification.verify_active_source(comm_const.Source.AIRPLAY)
    self._verify_active_source_playback(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_rule_of_silence_over_limit_leader(self):
    """ASE goes to standby after the source is muted more than 20 min
    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the leader for 20 mins
      -> No sound comes from Leader
      -> Sound comes from Follower
      3. Verify that after 20 mins power status of the products
      -> No sound comes from Leader
      -> Sound comes from Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._product_speaker_mute(self.leader)
    self._verify_no_sound_from_speaker(self.leader)
    self.follower.sound_verification.verify_sound(True)
    self.logger.info("Leader is muted")
    sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
    ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
#     standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
#     self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    self._verify_no_sound_from_speaker(self.leader)
    self.logger.info("Leader is muted")
    self.follower.sound_verification.verify_sound(True)

  def beolink_rule_of_silence_over_limit_on_follower(self):
    """ASE goes to standby after the source is muted more than 20 min
    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the Follower for 20 mins
      -> No sound comes from Follower
      -> Sound comes from Leader
      3. Verify that after 20 mins power status of the Follower i.e. "standby"
      -> No sound comes from Follower
      -> Sound comes from Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    start_time = time.time()
    self._product_speaker_mute(self.follower)
    self._verify_no_sound_from_speaker(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.logger.info("follower is muted")
#     sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
#     ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
    standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
    self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    actual_res = self.follower.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), actual_res, "The board is not in standby")
    self._verify_no_sound_from_speaker(self.follower)
    self.logger.info("Follower is muted")
    self.leader.sound_verification.verify_sound(True)

  def beolink_playback_next_previous_on_leader(self):
    """ A playback (next-previous) is controlled from the Leader

    Steps:
      1. Add 2 dlna tracks to a playqueue on the Leader
      2. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct
      -> play queue is empty on the Follower
      -> play queue is not empty on the Leader
      3. Send the command 'Next' to the Leader
      -> the Leader starts playing the next track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader
      4. Send the command 'Previous' to the Leader
      -> the Leader starts playing the previous track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    play_ids = self._add_tracks_to_play_queue_dlna(2)
    self.leader._play_queue.play_id_set(play_ids[0])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._join(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)
    self._verify_playqueue(self.leader, False)
    self._verify_playqueue(self.follower, True)
    self.logger.info("Sending next command to Leader")
    next_id = self.leader._play_queue.play_id_calculate(1)
    self.leader._streaming.forward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(next_id, play_now_id, "Next track did not start playing")
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.logger.info("Sending previous command to Leader")
    prev_id = self.leader._play_queue.play_id_calculate(-1)
    self.leader._streaming.backward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(prev_id, play_now_id, "Previous track did not start playing")

  def beolink_playback_pause_play_on_leader(self):
    """ A playback (pause-play) is controlled from the Leader

    Steps:
      1. Start tunein playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'
      2. Send the command 'Pause' to the Leader
      -> no sound from the Leader
      -> no sound from the Follower
      -> playback status is 'pause'
      3. Send the command 'Play' to the Leader
      -> the Leader starts playing
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self._play_join_verify_tunein()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.leader._streaming.pause()
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)
    self._leader_verify_playing_status(comm_const.PAUSE_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.leader._streaming.play()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_source_change_leader_for_expand(self):
    """ The sink goes through all changes of sources along with the Leader

    Steps:
      1. Start playing dlna from a Beolink Leader (expand) with the sound frequency M
      -> sound freq. M comes from the Follower
      -> sound freq. M comes from the Leader
      2. On the Leader switch to line in, start playing sound frequency N
      -> sound freq. N comes from the Follower
      -> sound freq. N comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_dlna(self.leader)
    self._expand(self.leader, self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA1[1])
    self._play_linein_source(self.leader)
    self.follower.sound_verification.verify_frequency(self._FREQUENCY)
    self.leader.sound_verification.verify_frequency(self._FREQUENCY)

  def beolink_source_change_follower_for_expand(self):
    """ The sink stops playing from the source if the sink selects a local source

    Steps:
      1. Start playing dlna from a Beolink Leader (expand) with the sound frequency M
      -> sound freq. M comes from the Follower
      -> sound freq. M comes from the Leader
      2. On the Follower switch to dlna, play sound frequency N
      -> sound freq. N comes from the Follower
      -> sound freq. M comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_dlna(self.leader)
    self._expand(self.leader, self.follower)
    self._verify_active_source_playback(self.leader, self.follower)
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA1[1])
    self.follower.dlna_client.play_track(self.follower.dlna_server.URL_DLNA2, 10)
    self.follower.sound_verification.verify_frequency(self.follower.dlna_server.URL_FREQ_DLNA2[1])
    self.leader.sound_verification.verify_frequency(self.leader.dlna_server.URL_FREQ_DLNA1[1])

  def beolink_rule_of_silence_over_limit_leader_for_expand(self):
    """ASE goes to standby after the source is muted more than 20 min
    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the leader for 20 mins
      -> No sound comes from Leader
      -> Sound comes from Follower
      3. Verify that after 20 mins power status of the products
      -> No sound comes from Leader
      -> Sound comes from Follower
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._product_speaker_mute(self.leader)
    self._verify_no_sound_from_speaker(self.leader)
    self.follower.sound_verification.verify_sound(True)
    self.logger.info("Leader is muted")
    sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
    ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
#     standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
#     self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    self._verify_no_sound_from_speaker(self.leader)
    self.logger.info("Leader is muted")
    self.follower.sound_verification.verify_sound(True)

  def beolink_rule_of_silence_over_limit_follower_for_expand(self):
    """ASE goes to standby after the source is muted more than 20 min
    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Mute the Follower for 20 mins
      -> No sound comes from Follower
      -> Sound comes from Leader
      3. Verify that after 20 mins power status of the Follower i.e. "standby"
      -> No sound comes from Follower
      -> Sound comes from Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._product_speaker_mute(self.follower, 0)
    start_time = time.time()
    self._verify_no_sound_from_speaker(self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.logger.info("follower is muted")

#     sleep_timeout = datetime.timedelta(hours=00, minutes=22, seconds=20).seconds
#     ASEHelpers.test_timeout(self.logger, sleep_timeout, "Waiting for standby.")
    standby_timeout = datetime.timedelta(hours=00, minutes=20, seconds=00).seconds
    self.follower._power_state.time_detect(comm_const.POWER_STATE_STANDBY, start_time, standby_timeout, 30)

    actual_res = self.follower.tal_http.get_power_state()
    self.assertEqual("standby", actual_res, "The board is not in standby")
    self._verify_no_sound_from_speaker(self.follower)
    self.logger.info("Follower is muted")
    self.leader.sound_verification.verify_sound(True)

  def beolink_standby_follower_for_expand(self):
    """ The Follower goes to standby, but Leader continues playing

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'Standby' to the Follower
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    power_status_follower = self._standby(self.follower)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_all_standby_leader_for_expand(self):
    """ Both the Follower and the Leader go to standby

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'AllStandby' to the Leader
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> no sound from the Leader
      -> power management's status on the Leader is 'standby

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.verification.verify_playback(self.leader.sound_verification)
    self.follower.verification.verify_playback(self.follower.sound_verification)

    power_status_follower = self._standby(self.leader, all_standby=True)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    power_status_leader = self.leader.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_leader.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.verification.verify_no_playback(self.leader.sound_verification)
    self.follower.verification.verify_no_playback(self.follower.sound_verification)

  def beolink_all_standby_follower_for_expand(self):
    """ Both the Follower and the Leader go to standby

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Send the command 'AllStandby' to the Follower
      -> no sound from the Follower
      -> power management's status on the Follower is 'standby
      -> no sound from the Leader
      -> power management's status on the Leader is 'standby

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    power_status_follower = self._standby(self.follower, all_standby=True)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    power_status_leader = self.leader.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_leader.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_verify_leader_can_become_follower_for_expand(self):
    """ To verify if leader can become the follower of other session

    Prerequisites:
      - there are 3 ASE products in the network
    Steps:
      1. Start playing from a Beolink Product A Leader
      -> Expand the source of Product A on Product B
      -> sound comes from the product B (Follower)
      -> sound comes from the product A (Leader)
      2. Start playing on a product C
      3. Send expand command to product A
      -> Verify that product A and product C are in multiroom session
      -> sound comes from the product C
      -> sound comes from the product A
      -> verify active source of product C, product A should be same

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_deezer(self.follower1)
    self._expand(self.follower1, self.leader)
    self.leader.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower1)

  def beolink_verify_follower_can_become_follower_for_expand(self):
    """ To verify if Follower can become the follower of other session

    Prerequisites:
      - there are 3 ASE products in the network
    Steps:
      1. Start playing from a Beolink Product A Leader
      -> Expand the source of Product A on Product B
      -> sound comes from the product B (Follower)
      -> sound comes from the product A (Leader)
      2. Start playing on a product C
      3. Send expand command to product B
      -> sound comes from the product C
      -> sound comes from the product A
      -> verify active source of product B, product C should be same

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._play_deezer(self.follower1)
    self._expand(self.follower1, self.follower)
    self.follower.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.follower1, self.follower)

  def beolink_playback_next_previous_on_leader_expand(self):
    """ A playback (next-previous) is controlled from the Leader

    Steps:
      1. Add 2 dlna tracks to a playqueue on the Leader
      2. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct
      -> play queue is empty on the Follower
      -> play queue is not empty on the Leader
      3. Send the command 'Next' to the Leader
      -> the Leader starts playing the next track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader
      4. Send the command 'Previous' to the Leader
      -> the Leader starts playing the previous track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    play_ids = self._add_tracks_to_play_queue_dlna(2)
    self.leader._play_queue.play_id_set(play_ids[0])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._expand(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)
    self._verify_playqueue(self.leader, False)
    self._verify_playqueue(self.follower, True)
    self.logger.info("Sending next command to Leader")
    next_id = self.leader._play_queue.play_id_calculate(1)
    self.leader._streaming.forward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(next_id, play_now_id, "Next track did not start playing")
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.logger.info("Sending previous command to Leader")
    prev_id = self.leader._play_queue.play_id_calculate(-1)
    self.leader._streaming.backward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(prev_id, play_now_id, "Previous track did not start playing")

  def beolink_playback_pause_play_on_leader_expand(self):
    """ A playback (pause-play) is controlled from the Leader

    Steps:
      1. Start tunein playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'
      2. Send the command 'Pause' to the Leader
      -> no sound from the Follower
      -> not sound from the Leader
      -> playback status is 'pause'
      3. Send the command 'Play' to the Leader
      -> the Leader starts playing
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.leader._streaming.pause()
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)
    self._leader_verify_playing_status(comm_const.PAUSE_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.leader._streaming.play()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_volume_level_leader_expand(self):
    """ A local operation volume level is not sent to the sourcing product

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Volume up on Leader
      -> Volume on Follower -- no changes
      -> Volume on Leader has been increased
      3. Volume down on Leader
      -> Volume on Follower -- no changes
      -> Volume on Leader has been decreased

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    volume_before_change_follower = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr = self.leader.tal_http.get_sound_volume_level()
    volume_level_bnr_after_increase = self._volume_increase(self.leader)
    volume_difference = volume_level_bnr_after_increase - volume_level_bnr
    volume_diff = 10
    self.assertEqual(volume_difference, volume_diff, "volume is not increased as expected")
    self._verify_volume_after_change(self.follower, volume_before_change_follower)
    volume_level_bnr = self.leader.tal_http.get_sound_volume_level()
    volume_level_bnr_after_change = self._volume_decrease(self.leader)
    volume_difference = volume_level_bnr - volume_level_bnr_after_change
    self.assertEqual(volume_difference, volume_diff, "Volume level different")
    self._verify_volume_after_change(self.follower, volume_before_change_follower)

  def beolink_playback_next_previous_on_follower_expand(self):
    """ A playback (next-previous) is controlled from the Follower

    Steps:
      1. Add 2 dlna tracks to a playqueue on the Leader
      2. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> info about sources at /BeoZone/Zone/ActiveSources is correct
      -> play queue is empty on the Follower
      -> play queue is not empty on the Leader
      3. Send the command 'Next' to the Follower
      -> the Leader starts playing the next track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader
      4. Send the command 'Previous' to the Follower
      -> the Leader starts playing the previous track in the queue: get info from the play queue
      -> sound comes from the Follower
      -> sound comes from the Leader

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    play_ids = self._add_tracks_to_play_queue_dlna(2)
    self.leader._play_queue.play_id_set(play_ids[0])
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._expand(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower)
    self._verify_playqueue(self.leader, False)
    self._verify_playqueue(self.follower, True)
    next_id = self.leader._play_queue.play_id_calculate(1)
    self.logger.info("Sending next command to follower")
    self.follower._streaming.forward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(next_id, play_now_id, "Next track did not start playing")
    prev_id = self.leader._play_queue.play_id_calculate(-1)
    self.logger.info("Sending previous command to follower")
    self.follower._streaming.backward()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    play_now_id = self.leader.tal_http.get_play_queue_playnowid()
    self.assertEqual(prev_id, play_now_id, "Previous track did not start playing")

  def beolink_playback_pause_play_on_follower_expand(self):
    """ A playback (pause-play) is controlled from the Follower

    Steps:
      1. Start dlna playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'
      2. Send the command 'Pause' to the Follower
      -> no sound from the Follower
      -> no sound from the Leader
      -> playback status is 'pause'
      3. Send the command 'Play' to the Follower
      -> the Leader starts playing
      -> sound comes from the Follower
      -> sound comes from the Leader
      -> playback status is 'playing'

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    timeout = 15
    ASEHelpers.test_timeout(self.logger, timeout)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)
    self.follower._streaming.pause()
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PAUSE_STATE)
    self.follower._streaming.play()
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_volume_level_follower_expand(self):
    """ A local operation volume level is not sent to the sourcing product

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Volume up on Follower
      -> Volume on Follower has been increased
      -> Volume on Leader -- no changes
      3. Volume down on Follower
      -> Volume on Follower has been decreased
      -> Volume on Leader -- no changes

     Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    volume_before_change_leader = self.leader.tal_http.get_sound_volume_level()
    volume_level_bnr = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr_after_increase = self._volume_increase(self.follower)
    volume_difference = volume_level_bnr_after_increase - volume_level_bnr
    volume_diff = 10
    self.assertEqual(volume_difference, volume_diff, "volume is not increased as expected")
    self._verify_volume_after_change(self.leader, volume_before_change_leader)
    volume_level_bnr = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr_after_change = self._volume_decrease(self.follower)
    volume_difference = volume_level_bnr - volume_level_bnr_after_change
    self.assertEqual(volume_difference, volume_diff, "Volume level different")
    self._verify_volume_after_change(self.leader, volume_before_change_leader)

  def beolink_verify_volume_on_leader_when_in_distributing_only_mode_for_expand(self):
    """ Verify volume change on Leader when leader is in distributing only mode

    Steps:
      1. Start playing from a Beolink Leader (expand)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Put leader into high power standby.
      -> No sound comes from the Leader
      -> Verify sound comes from Follower.
      3. Change the volume on Leader
      -> verify no change in volume on Leader
      -> verify no change in volume on Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Equipment: [sound_card]
    """
    self._play_expand_verify_tunein(self.leader, self.follower)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._standby(self.leader)
    timeout = 2
    ASEHelpers.test_timeout(self.logger, timeout)
    volume_before_change_follower = self.follower.tal_http.get_sound_volume_level()
    volume_level_bnr = self.leader.tal_http.get_sound_volume_level()
    try:
      self._volume_increase(self.leader)
    except AssertionError:
      volume_level_bnr_after = self.leader.tal_http.get_sound_volume_level()
      self.assertEqual(volume_level_bnr, volume_level_bnr_after, "Volume level increased on leader")
    self._verify_volume_after_change(self.follower, volume_before_change_follower)

# Link/Borrow
  def beolink_standby_on_leader_in_expand_experience(self):
    """ To verify the expanded experience when standby command is sent to leader.

   Steps:
      1. Start playing from a Beolink Leader (expand)
      -> Sound comes from the Follower
      -> Sound comes from the Leader
      2. Send the command 'Standby' to the Leader
      -> No sound from the Leader
      -> Sound comes from the Follower
      -> Power management's status on the product A is 'standby'.

    Hyperion::
     @Role1: Leader
     @Role2: Follower
     @Equipment: [sound_card]
    """
    self._play_tunein(self.leader)
    self._expand(self.leader, self.follower)
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader.sound_verification.verify_sound(True)
    self.follower.sound_verification.verify_sound(True)
    self._standby(self.leader)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_sound(True)

  def beolink_power_off_on_follower(self):
    """ To verify the joined experience when follower gets switched off during playback.
    Steps:
      1. Start playing from a Beolink Leader (join)
      -> sound comes from the Follower
      -> sound comes from the Leader
      2. Power off follower
      -> Verify that they are not in joined session.
      -> Verify playback on Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Equipment: [sound_card]
    """
    self._play_join_verify_tunein()
    self.follower.sound_verification.verify_sound(True)
    self.leader.sound_verification.verify_sound(True)
    res = self.follower.tal.hard_reboot()
    if not res:
      raise AssertionError("BNR is not running")
    self.leader.sound_verification.verify_sound(True)
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_can_join_the_ongoing_experience_in_the_same_network_while_playing_linked_source(self):
    """ Verify that Product A can join the ongoing experience in the same network while playing linked source.

    Precondition:-
     - Product A, Product B and Product C are in same network.
     - Product B is connected to Product A as a primary Product
     - Product C is  connected to Product A as a secondary product
     - Local source playback on Product C is on going.

    Steps:
     1. Start playing link source on Product A using BNR/T20 remote.
     -> Verify playback on product A
     2. Send join command to Product A.
     -> Verify playback on Product A and Product C.
     -> Sound  comes from the Follower
     -> Sound comes from the Leader

    Hyperion::
     @Role1: Leader
     @Role2: Follower
     @Role3: Follower1
     @Equipment: [sound_card]
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    secondary_friendly_name = self._product_friendly_name(self.follower1)
    follower1_jid = self._product_jid_get(self.follower1)
    self._select_secondary_product(follower1_jid, secondary_friendly_name)
    self._play_deezer(self.follower1)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._join(self.leader)
    self.leader.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)
    self._verify_active_source_playback(self.leader, self.follower1)

  def beolink_source_can_be_expanded_when_product_is_playing_link_source(self):
    """ Verify that Product C can expand it source to Product A, when Product A is playing linked source

    Precondition:-
      - Product A, Product B and Product C are in same network.
      - Product B is connected to Product A as a primary Product
      - Product C is  connected to Product A as a secondary product
      - Local source playback on Product C is on going.

    Steps:
      1. Start playing link source on Product A using BNR/T20 remote.
      -> Verify playback on product A
      2. Expand the local source of Product C to Product A.
      -> Verify playback on Product A and Product C.
      -> Sound  comes from the Follower
      -> Sound comes from the Leader

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
      @Equipment: [sound_card]
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    secondary_friendly_name = self._product_friendly_name(self.follower1)
    follower1_jid = self._product_jid_get(self.follower1)
    self._select_secondary_product(follower1_jid, secondary_friendly_name)
    self._play_deezer(self.follower1)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._expand(self.follower1, self.leader)
    timeout = 10
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower1)
    self.leader.sound_verification.verify_sound(True)
    self.follower1.sound_verification.verify_sound(True)

  def beolink_all_standby_while_playing_linked_source(self):
    """ Verify that all standby works properly while playing linked source on Product A

    Precondition:-
      - Product A, Product B and Product C are in same network.
      - Product B is connected to Product A as a primary Product
      - Product C is  connected to Product A as a secondary product

    Steps:
      1. Start playing link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give all standby command to Product A.
      -> No sound from the Follower's
      -> Power management's status on the Follower's is 'standby'
      -> No sound from the Leader
      -> Power management's status on the Leader is 'standby'

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    secondary_friendly_name = self._product_friendly_name(self.follower1)
    follower1_jid = self._product_jid_get(self.follower1)
    self._select_secondary_product(follower1_jid, secondary_friendly_name)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    power_status_leader = self._standby(self.leader, all_standby=True)
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_leader.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    power_status_follower = self.follower.tal_http.get_power_state()
    self.assertEqual(comm_const.POWER_STATE_STANDBY.lower(), power_status_follower.lower(), "The board is not in %s" % comm_const.POWER_STATE_STANDBY)
    self.leader.sound_verification.verify_no_sound(True)
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_no_linked_sources_are_played(self):
    """ Verify that no linked sources played when NO products are connected to Product A

    Precondition:-
      - Product A, Product B and Product C are in same network.
      - Product B is connected to Product A as a primary Product
      - Product C is  connected to Product A as a secondary product

    Steps:
      1. Open webpage of product A.
      2. Tab on Settings >> BeoLink >> link to other products tab.
      3. Select None as primary and secondary product connected to.
      4. Select link source on Product A using BNR/T20 remote.
      -> Verify playback on Product A. Playback should not start.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    secondary_friendly_name = self._product_friendly_name(self.follower1)
    follower1_jid = self._product_jid_get(self.follower1)
    self._select_secondary_product(follower1_jid, secondary_friendly_name)
    self.leader.webpage.driver.quit()
    self._leader_webpage_setup()
    self._select_primary_product("", primary_friendly_name)
    self._select_secondary_product("", secondary_friendly_name)
    try:
      self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower1)
    except Exception as exc:
      self.logger.info("Error Occurred while giving link command to product %s " % exc)

  def beolink_secondary_product_source_is_played_when_both_connected_products_are_ASE_products(self):
    """ Verify that Product A starts linked source of Product C(Secondary) which is connected to
    Product A as primary product.

    Precondition:-
      - Product A, Product B and Product C are in same network.
      - Product B is connected to Product A as a primary Product
      - Product C is  connected to Product A as a secondary product

    Steps:
      1. Open webpage of product A.
      2. Tab on Settings >> BeoLink >> link to other products tab.
      3. Select None as primary product connected to from webpage.
      4. Select link source on Product A using BNR/T20 remote.
      -> Verify that Product A starts playback of link source of secondary product (product C).

    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Role3: Follower1
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    secondary_friendly_name = self._product_friendly_name(self.follower1)
    follower1_jid = self._product_jid_get(self.follower1)
    self._select_secondary_product(follower1_jid, secondary_friendly_name)
    self.leader.webpage.driver.quit()
    self._leader_webpage_setup()
    self._select_primary_product("", primary_friendly_name)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower1)
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_active_source_playback(self.leader, self.follower1)

  def beolink_next_previous_on_product_b(self):
    """ Verify the Next/Previous command to Product B

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give Next command to Product B.
      -> Verify that next track/stations on product B and A.
      3. Give Previous command to Product B.
      -> Verify that Previous track/stations is playing on product B and A.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self.logger.info("To verify that product is in play state or not")
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.follower._streaming.forward()

    play_now_station_id_follower = self.follower.tal_http.get_play_queue_playnowid()
    self.logger.info("")
    self.logger.info("play_now_station_id_follower: %s" % play_now_station_id_follower)
    self.logger.info("Verifying notifications on the leader.")
    self.logger.info("")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    notifications_leader = self.leader.tal_http.get_notifications(100)
    self.leader.tal_http.stop_listening_to_notifications()

    correct_notification = False
    for notification in notifications_leader:
      self.logger.debug(notification)
      if (notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and
          notification.data.get('state', None) == comm_const.PLAY_STATE and
          notification.data.get('playQueueItemId', None) == play_now_station_id_follower):
        correct_notification = True
        break
    self.assertTrue(correct_notification, "Leader and follower are not playing same station")

  def beolink_next_previous_on_product_a(self):
    """ Verify the Next/Previous command to Product A

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give Next command to Product A.
      -> Verify that next track/stations is playing on product B and A.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.leader._streaming.forward()
    play_now_station_id_follower = self.follower.tal_http.get_play_queue_playnowid()
    self.logger.info("")
    self.logger.info("Verifying notifications on the leader.")
    self.logger.info("Verify that product is in play state or not")
    self.logger.info("")
    notifications_leader = self.leader.tal_http.get_notifications(100)
    correct_notification = False
    for notification in notifications_leader:
      if self._debug:
        self.logger.debug(notification)
      if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None) == comm_const.PLAY_STATE and notification.data.get('playQueueItemId', None) == play_now_station_id_follower:
        correct_notification = True
        break
    self.assertTrue(correct_notification, "Leader and follower are not playing same station %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
    self.leader.tal_http.stop_listening_to_notifications()

  def beolink_play_pause_on_product_b(self):
    """ Verify the Play/Pause command to Product B

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give Pause command to Product B.
      -> Verify that playback status on product B and A changed to Pause.
      3. Give Play command to Product B.
      -> Verify that playback status on product B and A changed to Play.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.logger.info("To verify that product is in pause state or not")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower._streaming.pause()
    self._leader_verify_playing_status(comm_const.PAUSE_STATE)
    self._follower_verify_playing_status(comm_const.PAUSE_STATE)
    self.logger.info("To verify that product is in play state or not")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower._streaming.play()
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_play_pause_on_product_a(self):
    """ Verify the Play/Pause command to Product A

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give Pause command to Product A.
      -> Verify that playback status on product B and A changed to Pause.
      3. Give Play command to Product A.
      -> Verify that playback status on product B and A changed to Play.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.logger.info("To verify that product is in pause state or not")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.leader._streaming.pause()
    self._leader_verify_playing_status(comm_const.PAUSE_STATE)
    self._follower_verify_playing_status(comm_const.PAUSE_STATE)
    self.logger.info("To verify that product is in play state or not")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.follower.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    self.leader._streaming.play()
    self._leader_verify_playing_status(comm_const.PLAY_STATE)
    self._follower_verify_playing_status(comm_const.PLAY_STATE)

  def beolink_volume_change_on_product_b(self):
    """ Verify that volume is increased/decreased on Product B, Volume is not getting changed on product A.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Increase volume on Product B.
      -> Verify volume should not get changed on Product A.
      -> Verify increase in volume on Product B.
      3. Decrease volume on Product B.
      -> Verify volume should not get changed on Product A.
      -> Verify decrease in volume on Product B.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    speaker_volume_leader_before = self.leader.tal_http.get_sound_volume_level()
    speaker_volume = self.follower.tal_http.get_sound_volume_level()
    set_volume = speaker_volume + 10
    self.follower.tal_http.set_sound_volume_level(set_volume)
    speaker_volume = self.follower.tal_http.get_sound_volume_level()
    self.assertEqual(speaker_volume, set_volume, "Volume is different")
    speaker_volume = self.leader.tal_http.get_sound_volume_level()
    self.assertEqual(speaker_volume_leader_before, speaker_volume, "Different volume")

  def beolink_volume_change_on_product_a(self):
    """ Verify that volume is increased/decreased on Product A, Volume is not getting changed on product B

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Increase volume on Product A.
      -> Verify volume should not get changed on Product B.
      -> Verify increase in volume on Product A.
      3. Decrease volume on Product A.
      -> Verify volume should not get changed on Product B.
      -> Verify decrease in volume on Product A.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    speaker_volume_follower_before = self.follower.tal_http.get_sound_volume_level()
    speaker_volume = self.leader.tal_http.get_sound_volume_level()
    set_volume = speaker_volume + 10
    self.leader.tal_http.set_sound_volume_level(set_volume)
    speaker_volume = self.leader.tal_http.get_sound_volume_level()
    self.assertEqual(speaker_volume, set_volume, "Volume is different")
    speaker_volume = self.follower.tal_http.get_sound_volume_level()
    self.assertEqual(speaker_volume_follower_before, speaker_volume, "Differnt volume")

  def beolink_mute_on_product_b_when_it_is_playing_linked_source(self):
    """ Verify mute on Product B when Product A is playing linked source.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give mute command to Product B
      -> Verify that status is muted on Product B.
      -> verify that status is unmuted on Product A.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._product_speaker_mute(self.follower)
    self._verify_mute_or_unmute(self.follower)
    self._verify_mute_or_unmute(self.leader, is_muted=False)

  def beolink_mute_on_product_a_when_it_is_playing_linked_source(self):
    """ Verify mute on Product A when Product A is playing linked source.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Give mute command to Product A.
      -> Verify that status is muted on Product A.
      -> verify that status is unmuted on Product B.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._product_speaker_mute(self.leader)
    self._verify_mute_or_unmute(self.leader)
    self._verify_mute_or_unmute(self.follower, is_muted=False)

  def beolink_source_change_on_product_a_when_product_b_is_in_network_standby_mode(self):
    """ Verify source changed on Product A when it is playing Product B's link source

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Product B is in network standby mode.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Change linkable source on Product A.
      -> Verify that Product A change the linked source as per command given.
      -> Power management's status on the product B is 'standby'.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._standby(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._verify_and_play_link_source((comm_const.Source.MUSIC).lower(), self.follower)
    self.leader.verification.verify_active_source((comm_const.Source.DEEZER).lower() + ":" + follower_jid)

  def beolink_source_change_on_product_a_when_local_playback_is_going_on_product_b(self):
    """ Verify source changed on Product A when it is playing Product B's link source

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Change linkable source on Product A.
      -> Verify that Product B and Product A should play the same sources.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._verify_and_play_link_source((comm_const.Source.MUSIC).lower(), self.follower)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_source_change_on_product_b(self):
    """ Verify source changed on Product B when Product A is playing Product B's link source.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Change linkable source on Product B.
      -> Verify that Product B and Product A should play the same sources.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self._play_deezer(self.follower)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_playback_of_linked_source_when_disconnected_from_webpage(self):
    """ Verify the playback of linked source on Product A when Product B is disconnected from webpage.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Any local source playback is going on Product B.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Open webpage of product A.
      3. Tab on Settings >> BeoLink >> link to other products tab.
      4. Select None as primary product connected to from webpage.
      -> Verify that Product B and Product A should play the same sources.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._play_deezer(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.leader.webpage.driver.quit()
    self._leader_webpage_setup()
    self._select_primary_product("", primary_friendly_name)
    self._verify_active_source_playback(self.leader, self.follower)

  def beolink_playback_of_linked_source_when_product_b_is_in_network_standby_mode(self):
    """ Verify the playback of linked source on Product A when Product B is disconnected from webpage.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Product B in network standby mode.

    Steps:
      1. Select Link source on Product A using BNR/T20 remote.
      -> Verify playback on product A.
      2. Open webpage of product A.
      3. Tab on Settings >> BeoLink >> link to other products tab.
      4. Select None as primary product connected to from webpage.
      -> Verify that playback on Product A.
      -> no sound from the Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._standby(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.leader.webpage.driver.quit()
    self._leader_webpage_setup()
    self._select_primary_product("", primary_friendly_name)
    self.logger.info("")
    self.logger.info("Verifying notifications on the leader.")
    self.logger.info("Verify that product is in play state or not")
    self.logger.info("")
    self.leader.tal_http.start_listening_to_notifications(self._LISTENING_TIME)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader._streaming.play()
    notifications_leader = self.leader.tal_http.get_notifications(100)
    correct_notification = False
    for notification in notifications_leader:
      if self._debug:
        self.logger.debug(notification)
      if notification.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and notification.data.get('state', None) == comm_const.PLAY_STATE:
        correct_notification = True
        break
#     self.assertTrue(correct_notification, "Leader did not receive the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
    ASEHelpers.verify_notification_received(self.logger, correct_notification, ase_const.PROGRESS_INFORMATION_NOTIFICATION, 'state', comm_const.PLAY_STATE)
    self.logger.info("Verification successful")
    self.leader.tal_http.stop_listening_to_notifications()
    self.follower.sound_verification.verify_no_sound(True)

  def beolink_play_linked_sources_via_BNR_when_product_b_is_in_network_standby_mode(self):
    """ Verify that all the linked sources are playable via BNR/T20 when local playback is going on Product B.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Product B in network standby mode.

    Steps:
      1. Start playing all Link source via BNR.
      -> Verify the playback on Product A.
      -> no sound from the Follower

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_deezer(self.follower)
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._standby(self.follower)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    self.follower.sound_verification.verify_no_sound(True)
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    timeout = 20
    ASEHelpers.test_timeout(self.logger, timeout)
    self._verify_and_play_link_source((comm_const.Source.MUSIC).lower(), self.follower)
    self.follower.sound_verification.verify_no_sound(True)
    self.leader.verification.verify_active_source((comm_const.Source.DEEZER).lower() + ":" + follower_jid)

  def beolink_play_linked_sources_via_BNR_T20_when_local_playback_is_going_on_product_b(self):
    """ Verify that all the linked sources are playable via BNR/T20 when local playback is going on Product B.

    Precondition:
      - Product A and Product B(Any Product) are in same network.
      - Product B is connected to Product A as a primary Product
      - Product B is playing Local source

    Steps:
      1. Start playing Link source via T20 remote.
      -> Verify that Product B and Product A should play the same sources.

    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._play_deezer(self.follower)
    primary_friendly_name = self._product_friendly_name(self.follower)
    follower_jid = self._product_jid_get(self.follower)
    self._select_primary_product(follower_jid, primary_friendly_name)
    self._verify_and_play_link_source((comm_const.Source.RADIO_BNR).lower(), self.follower)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader._streaming.play()
    self.leader.verification.verify_active_source(comm_const.Source.RADIO)
    self.follower.verification.verify_active_source(comm_const.Source.RADIO)
    self._verify_and_play_link_source((comm_const.Source.MUSIC).lower(), self.follower)
    timeout = 5
    ASEHelpers.test_timeout(self.logger, timeout)
    self.leader._streaming.play()
    self.leader.verification.verify_active_source((comm_const.Source.DEEZER).lower() + ":" + follower_jid)
    self.follower.verification.verify_active_source(comm_const.Source.DEEZER)


if __name__ == "__main__":
  """ """
  # ===============================================================================
  # creation of an xml file with test cases
  # ===============================================================================
  # integration test
  from BTE.src.TestRunner import BeoTestRunner
  from BTE.src.CommonTestClasses import BeoTestResult
  import BTE.src.Constants as const

  test_case_arguments = ""
  result = BeoTestResult()
  test_resources = {"ASE_EZ2": {'resource_role': ['leader'],
                                # 'sw_path': 'STAF2NMMTest_wr203Debug_b3_r58304.tgz',
                                const.start_staf_app: False},
                    "ASE_Beolink_1": {'resource_role': ['follower'],
                                      # 'sw_path': 'STAF2NMMTest_wr203Debug_b3_r58304.tgz',
                                      const.start_staf_app: False},
                    "ASE_Beolink_2": {'resource_role': ['follower1'],
                                      # 'sw_path': 'STAF2NMMTest_wr203Debug_b3_r58304.tgz',
                                      const.start_staf_app: False}
                    }
  test_id = None
  test_module_name = "ASE.src.BeoLink"
  test_class_name = "BeoLink"

#   test_case_name = "beolink_mute_on_product_a_when_it_is_playing_linked_source"  # OK
#   test_case_name = "beolink_source_can_be_expanded_when_product_is_playing_link_source"  # Drop down menu value not visible! '2897.1293024.00092283%40products.bang-olufsen.com'
#   test_case_name = "beolink_power_off_on_follower"  # No power manager found. Skipping reboot
#   test_case_name = "beolink_all_standby_while_playing_linked_source"  # Drop down menu value not visible! '2897.1293024.00092283%40products.bang-olufsen.com'
#   test_case_name = "beolink_can_join_the_ongoing_experience_in_the_same_network_while_playing_linked_source"  # Drop down menu value not visible! '2897.1293024.00092283%40products.bang-olufsen.com'
  test_case_name = "beolink_no_linked_sources_are_played"  # Drop down menu value not visible! '2897.1293024.00092283%40products.bang-olufsen.com'
#   test_case_name = "beolink_secondary_product_source_is_played_when_both_connected_products_are_ASE_products"  # Drop down menu value not visible! '2897.1293024.00092283%40products.bang-olufsen.com'
#   test_case_name = "beolink_play_pause_on_product_a"  # Notification 'PROGRESS_INFORMATION' containing key 'state' with the status 'play' was not received! line 3473
#   test_case_name = "beolink_play_pause_on_product_b"  # Notification 'PROGRESS_INFORMATION' containing key 'state' with the status 'play' was not received! line 3349
#   test_case_name = "beolink_verify_bluetooth_can_interrupt_multiroom_experience"  # There is not sound from speakers line 2242
#   test_case_name = "beolink_playback_pause_play_on_leader_expand"  # Notification 'PROGRESS_INFORMATION' containing key 'state' with the status 'pause' was not received! line 2779
#   test_case_name = "beolink_source_change_follower_for_expand"  # There is not sound from speakers line 2476
#   test_case_name = "beolink_playback_pause_play_on_follower_expand"  # OK
#   test_case_name = "beolink_source_change_leader_for_expand"  # There is not sound from speakers line 2453
#   test_case_name = "beolink_power_off_on_leader"  # Power state 'standby' was not found inside allowed time frame. min: 00:19:30. max: 00:20:30.
#   test_case_name = "beolink_expand_on_multiple_products"  # There is not sound from speakers line 2063
#   test_case_name = "beolink_webpage_network_delay_wired"  # error in line 1558 -> 463 -> TALCommon 318 -> 409 (not implemented)
#   test_case_name = "beolink_webpage_sound_network_delay_wifi"  # error in line 1594 -> 463 -> TALCommon 318 -> 409 (not implemented)
#   test_case_name = "beolink_expand_experience_when_leader_start_sw_updating"  # not working due to window handling of open file...
#   test_case_name = "beolink_join_when_no_ongoing_experience_available"  # There is not sound from speakers line 1975
#   test_case_name = "beolink_play_expand_bluetooth"  # There is not sound from speakers line 1146
#   test_case_name = "beolink_playback_pause_play"  # OK
#   test_case_name = "beolink_play_expand_dlna"  # There is not sound from speakers line 1077
#   test_case_name = "beolink_leader_change_follower"  # There is not sound from speakers line 1344
#   test_case_name = "beolink_play_join_bluetooth"  # There is not sound from speakers line 1011
# http://hyperion.bang-olufsen.dk/Test/testresults.php?ButtonClicked=Compare&test131501
  test_case_roles = ['leader', 'follower', 'follower1']
  test_case_known_error = None
  test_case_setup = None
  test_case_script = None
  test_case_cleanup = None
  tr = BeoTestRunner(result, test_resources, test_id, test_module_name, test_class_name, test_case_name, test_case_arguments,
                     test_case_setup, test_case_script, test_case_cleanup, roles=test_case_roles, local_run=False)
  tr.run()
