"""
  Test cases for the component: Remote Control T20

  @copyright: 2016 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: VSU
"""

import time

from BTE.src.CommonTestClasses import BeoTestClass
from Common.src.Resources import IRTRANS
from BTE.src.CustomExceptions import TestAssertionError
from Common.src.ITunes import ITunesState

import Common.src.Constants as comm_const
import Common.ASE.CommonLib.src.Constants as ase_const
import ASE.src.Helpers as ASEHelpers
import Common.src.Helpers as Helpers


class RemoteControlIR(BeoTestClass):
  """test cases for  T20 remote control
  Using IR telegrams with F0, F17 and F20 formats
  """

  # pylint:disable=no-member
  def setUp(self):
    """
    """

    if hasattr(self, 'leader'):
      self._setup_dut(self.leader)
      self.leader.tal_http.power_state_standby_standby()
    if hasattr(self, 'follower'):
      self._setup_dut(self.follower)
      self.follower.tal_http.power_state_standby_standby()
    else:
      self.nav_ltap.target.set_IR_telegram_format_F17(IRTRANS.IRAddress.IRA1,
                                                      IRTRANS.NetworkBit.local,
                                                      IRTRANS.AudioVideo.audio)
      self._verification = ASEHelpers.Verification(self.logger,
                                                 self.tal_http,
                                                 self.assertFalse,
                                                 self.assertEqual)

      ASEHelpers.check_tunein_url(self.tal, self.tal_http, self.selenium_server, self.chromecast, self.skipTest)

      self._tunein_account = comm_const.TUNEIN_ACCOUNT

      self._tunein_client = ASEHelpers.TuneInClientHelper(self.tal_http, self.logger, self._tunein_account, self.skipTest, self.tal)

      Helpers.clear_queue(self.tal_http)
      self.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
      self.product_fiendly_name = self.tal_http.get_product_friendly_name()
      if self.apple_communicator is not None:
        self.apple_communicator.ip_address = self.tal.get_ip()
        self.apple_communicator.create_client(60)
    self.logger.info("Setup end")

  def tearDown(self):
    """
    """
    self.logger.info("stopping the stream")
    if hasattr(self, 'leader'):
      self._teardown_dut(self.leader)
    if hasattr(self, 'follower'):
      self._teardown_dut(self.follower)
    else:
      self.tal_http.stream_stop()

  def _setup_dut(self, product):
    """ product setup
    @param product: Leader/Follower ex self.leader or self.follower
    @type product: String
    """
    product.nav_ltap.target.set_IR_telegram_format_F17(IRTRANS.IRAddress.IRA1,
                                                     IRTRANS.NetworkBit.local,
                                                     IRTRANS.AudioVideo.audio)
    product._deezer_client = ASEHelpers.DeezerClientHelper(product.tal_http,
                                                           self.logger,
                                                           ASEHelpers.get_deezer_account(self.tal))
    product.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
    Helpers.clear_queue(product.tal_http)
    product.sound_verification = ASEHelpers.SoundVerification(self.logger,
                                                              product.sound_card,
                                                              product.tal_http,
                                                              self.assertFalse,
                                                              self.assertEqual, 50)

  def _teardown_dut(self, product):
    """ product teardown
    @param product: Leader/Follower ex self.leader or self.follower
    @type product: String
    """
    product.tal_http.stream_stop()

  def _verify_wind_and_rewind(self, method):
    """ send wind command and verify
    @param method: Wind/rewind command
    @type method: String
    """
    self.tal_http.start_listening_to_notifications(100)
    time.sleep(5)
    res = self.tal_http.get_notifications(80)
    correct_notification = False
    for i in res:
      if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == comm_const.PLAY_STATE:
        playback_position = i.data.get('position', None)
        correct_notification = True
        break
    self.assertTrue(correct_notification, "Product does not received the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
    self.tal_http.stop_listening_to_notifications()
    self.logger.info("To verify product is in play state and track seek position is greater than previous seek position")
    self.tal_http.start_listening_to_notifications(100)

    if method == comm_const.WIND:
      self.nav_ltap.wind()
      correct_notification = False
      time.sleep(20)
      res = self.tal_http.get_notifications(80)
      for i in res:
        if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == comm_const.PLAY_STATE and i.data.get('position', None) >= playback_position:
          correct_notification = True
          break
      self.assertTrue(correct_notification, "Product does not received the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
      self.logger.info("Verification successful")
      self.tal_http.stop_listening_to_notifications()

    elif method == comm_const.REWIND:
      self.nav_ltap.rewind()
      correct_notification = False
      time.sleep(20)
      res = self.tal_http.get_notifications(80)
      for i in res:
        if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == comm_const.PLAY_STATE and i.data.get('position', None) <= playback_position:
          correct_notification = True
          break
      self.assertTrue(correct_notification, "Product does not received the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
      self.logger.info("Verification successful")
      self.tal_http.stop_listening_to_notifications()
    else:
      raise TestAssertionError("Invalid input: It can be wind or rewind state")

  def _play_itunes_and_verify(self):
    """ Method will play itunes and verify the play state and active source
    """
    self.logger.info("iTunes initiated on source")
    hres = self.apple_communicator.execute_apple_script('%s "%s"' % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                                     self.product_fiendly_name))
    self.logger.info("the apple script '%s' returns %s" % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                           hres))
    if hres != ['0']:
      raise TestAssertionError("Cannot select speakers")
    self.apple_communicator.itunes_set_volume(50)
    self.apple_communicator.itunes_start_play_music()
    time.sleep(20)
    playstate = self.apple_communicator.itunes_get_play_state()
    self.logger.info("iTunes play state is %s" % playstate)
    if ITunesState.PLAYING != playstate:
      raise TestAssertionError("iTunes is not playing")
    self._verification.verify_active_source(comm_const.Source.AIRPLAY)

  def _join(self, product):
    """ Sending join command to product
    @param product: Leader/Follower ex self.leader or self.follower
    @type product: String
    """
    product.tal_http.send_http_command_post(comm_const.BEO_ONE_WAY_JOIN, '{"toBeReleased": true}')
    product.tal_http.send_http_command_post(comm_const.BEO_ONE_WAY_JOIN_RELEASE, '')
    time.sleep(20)

  def _next_and_previous_and_verify(self):
    """ Send next command from T20 remote and verify that next command is accepted
    """
    play_ids = self._tunein_client.add_stations_to_play_queue(3)
    self.tal_http.play_queue_play(play_ids[0])
    play_now_station_id = self.tal_http.get_play_queue_playnowid()
    next_value = int(str(play_now_station_id).split('-')[1]) + 1
    next_id = "plid-" + str(next_value)
    self.logger.info(next_id)
    time.sleep(5)
    self.nav_ltap.step_up()
    time.sleep(30)
    play_now_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(next_id, play_now_id, "Next track did not start playing")
    prev_value = int(str(play_now_id).split('-')[1]) - 1
    prev_id = "plid-" + str(prev_value)
    self.logger.info(prev_id)
    time.sleep(5)
    self.nav_ltap.step_down()
    time.sleep(30)
    play_now_station_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(prev_id, play_now_station_id, "Previous track did not start playing")

  def _mute_or_unmute_verify(self, is_muted=True):
    """This method will verify if the source is mute or unmute from the BNR
    @param product: Product Leader/ Follower on which IR command to send
    @type product: String
    @param is_muted: to verify mute state is True or Not
    @type is_muted: Boolean
    """
    self.nav_ltap.mute()
    if is_muted == False:
      self.nav_ltap.mute()
    time.sleep(20)
    sound_state = self.tal_http.is_speaker_muted()
    self.logger.info("Sound muted or not:%s" % sound_state)
    if is_muted:
      self.logger.info("Expected mute state found: %s" % sound_state)
      self.assertTrue(sound_state, "DUT is still in unmuted state")
    else:
      self.logger.info("Expected mute state found: %s" % sound_state)
      self.assertFalse(sound_state, "DUT is still in muted state")

  def _standby_and_verify(self, product, standby=True):
    """ send standby and all standby command
    @param product: product Leader/Follower
    @type product: String
    @param standby: to verify standby/all standby
    @type standby: Boolean
    """
    if standby:
      product.nav_ltap.standby()
      time.sleep(20)
      if product.tal_http.get_power_state() != comm_const.POWER_STATE_STANDBY:
        raise TestAssertionError("The board is not in standby")

    else:
      product.nav_ltap.all_standby()
      time.sleep(20)
      if product.tal_http.get_power_state() != comm_const.POWER_STATE_ALLSTANDBY:
        raise TestAssertionError("The board is not in allstandby")

  def _volume_up_down_verify(self, pause=False):
    """ Increase/ Decrease volume and verify
    @param product: product Leader/Follower
    @type product: String
    @param pause: to verify Increase/ Decrease in volume in pause state
    @type pause: Boolean
    """
    volume_level_before_set = self.tal_http.get_sound_volume_level()
    if pause == False:
      self.nav_ltap.volume_up()
      time.sleep(5)
      volume_level_after_increase = self.tal_http.get_sound_volume_level()
      self.assertEqual(volume_level_before_set + 1, volume_level_after_increase, "Volume Does not increase")
      self.nav_ltap.volume_down()
      time.sleep(5)
      volume_level_after_decrease = self.tal_http.get_sound_volume_level()
      self.assertEqual(volume_level_after_increase - 1, volume_level_after_decrease, "Volume Does not increase")
    else:
      for i in range(100):
        self.nav_ltap.volume_up()
      volume_level_bnr = self.tal_http.get_sound_volume_level()
      self.assertEqual(volume_level_bnr, comm_const.VOLUME_LEVEL_MAX_PAUSE, "Volume set is different")
      for i in range(100):
        self.nav_ltap.volume_down()
      volume_level_bnr = self.tal_http.get_sound_volume_level()
      self.assertEqual(volume_level_bnr, comm_const.VOLUME_LEVEL_MIN_PAUSE, "Volume set is different")

  def _verify_playback_status_multiroom(self, product, playback_status):
    """ Increase/ Decrease volume and verify
    @param product: product Leader/Follower
    @type product: String
    @param playback_status: to verify playback status i.e. playing/pause
    @type playback_status: String
    """
    product.tal_http.start_listening_to_notifications(200)
    if playback_status == comm_const.PLAY_STATE:
      product.nav_ltap.play()
      time.sleep(20)
    elif playback_status == comm_const.PAUSE_STATE:
      product.nav_ltap.stop()
    else:
      raise TestAssertionError("Invalid input: It can be play or pause state")
    time.sleep(10)
    self.logger.info("To verify product status")
    res = product.tal_http.get_notifications(100)
    correct_notification = False
    for i in res:
      if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == playback_status:
        correct_notification = True
        break
    self.assertTrue(correct_notification, "Product does not received the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
    product.tal_http.stop_listening_to_notifications()
    self.logger.info("Verification successful")

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

  def _play_or_pause_and_verify(self, playback_status):
    """ Method to send play or pause command and verify playback status.
    @param playback_status: to verify playback status i.e. playing/pause
    @type playback_status: String
    """
    self.tal_http.start_listening_to_notifications(60)
    if playback_status == comm_const.PLAY_STATE:
      self.nav_ltap.play()
      time.sleep(30)
    elif playback_status == comm_const.PAUSE_STATE:
      self.nav_ltap.stop()
    else:
      raise TestAssertionError("Invalid input: It can be play or pause state")
    time.sleep(10)
    correct_notification = False
    res = self.tal_http.get_notifications(30)
    for i in res:
      if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == playback_status:
        self.logger.info("inside_if")
        self.logger.info(i)
        correct_notification = True
        break
    self.assertTrue(correct_notification, "Does not received the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)
    self.logger.info("Verification Successful")
    self.tal_http.stop_listening_to_notifications()

  def _set_option_programming(self, option):
    """ To set different option programming on product
    @param option: Different option programming to set ex 0,1,2,4
    @type option: Number
    """
    if option == 1:
      self.tal_http.nav_ltap.option1()
    elif option == 2:
      self.tal_http.nav_ltap.option2()
    elif option == 0:
      self.tal_http.nav_ltap.option0()
    else:
      self.logger.info("The option setting is out of scope")

  def remote_control_wind_using_t20(self):
    """Verify wind on ASE product using T20 remote

    Precondition:
      - Airplay playback is active on ASE product
    Steps:
      1. Send wind command from T20 remote to ASE product.
      -> Playback should get wind

    Hyperion::
      @Equipment: [apple_communicator]
    """
    self._play_itunes_and_verify()
    self._verify_wind_and_rewind(comm_const.WIND)
    self.logger.warn("Fails because of the bug ASE-1254")

  def remote_control_rewind_using_t20(self):
    """Verify rewind on ASE product using T20 remote

    Precondition:
      - Airplay playback is active on ASE product
    Steps:
      1. Send rewind command from T20 remote remote to ASE product.
      -> Playback should get rewind
    Hyperion::
      @Equipment: [apple_communicator]
    """
    self._play_itunes_and_verify()
    self._verify_wind_and_rewind(comm_const.REWIND)
    self.logger.warn("Fails because of the bug ASE-1254")

  def remote_control_unmute_when_playback_is_active(self):
    """ Verify unmute/mute on ASE product using T20 remote

    Precondition:
      - Playback is active on ASE product
    Steps:
      1. Send mute command to ASE product from T20 remote remote.
      -> Verify that sound is muted using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._mute_or_unmute_verify()

  def remote_control_unmute_when_sound_is_mute(self):
    """ Verify mute on ASE product using  T20 remote

    Precondition:
      - Playback is mute on ASE product
    Steps:
      1. Send mute command to ASE product from T20 remote remote.
      2. Send unmute command to ASE product from T20 remote remote.
      -> Verify that sound is unmuted using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._mute_or_unmute_verify(is_muted=False)

  def remote_control_volume_up_down_when_active_playback(self):
    """ Verify volume up/down on ASE product when playback is active using  T20 remote
    Precondition:
      - Playback is active on ASE product
    Steps:
      1. Send volume up command from T20 remote.
      -> Verify volume up using BNR
      2. Send volume down command from T20 remote.
      -> Verify volume down using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._volume_up_down_verify()

  def remote_control_volume_up_down_when_playback_is_pause(self):
    """ Verify volume up/down on ASE product when playback is active using  T20 remote

    Precondition:
      - Playback is pause on ASE product
    Steps:
      1. Send volume up/down command from T20 remote.
      -> Verify volume up/down range is 20-50 using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PAUSE_STATE)
    self._volume_up_down_verify(pause=True)

  def remote_control_next_previous_when_playback_is_active(self):
    """verify next previous tracks when playback is active

    Precondition:
      - Playback is active on ASE product
    Steps
      1. Send next command from T20 to ASE product
      -> Next track/station(as per the source) should start playing on ASE product
      2. Send previous command from T20 to ASE product
      -> Previous track/station(as per the source) should start playing on ASE product
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._next_and_previous_and_verify()

  def remote_control_next_previous_when_playback_is_pause(self):
    """verify next previous tracks when playback is pause

    Precondition:
      - Playback is pause on ASE product
    Steps
      1. Send next command from T20 to ASE product
      -> Playback should resume and Next track/station(as per the source) should start playing on ASE product
      2. Send previous command from T20 to ASE product
      -> Playback should resume and Previous track/station(as per the source) should start playing on ASE product
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PAUSE_STATE)
    self._next_and_previous_and_verify()

  def remote_control_next_previous_when_playback_is_mute(self):
    """verify next previous tracks when playback is mute

    Precondition:
      - Playback is mute on ASE product
    Steps
      1. Send next command from T20 to ASE product
      -> Next track/station(as per the source) should start playing on ASE product
      2. Send previous command from T20 to ASE product
      -> Previous track/station(as per the source) should start playing on ASE product
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._mute_or_unmute_verify()
    self._next_and_previous_and_verify()

  def remote_control_play_when_plaback_is_pause(self):
    """Verify play pause on ASE product using  T20

    Precondition:
      - Playback is pause on ASE product
    Steps:
      1. Send play command from T20 to ASE product
      -> Playback should get resumes
      2. Send pause command from T20 to ASE product.
      -> Playback should get pause
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PAUSE_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(20)
    self._play_or_pause_and_verify(comm_const.PAUSE_STATE)

  def remote_control_pause_when_playback_isactive(self):
    """Verify pause play on ASE product using  T20

    Precondition:
      - Playback is active on ASE product
    Steps:
      1. Send pause command from T20 to ASE product
      -> Playback should get paused
      2. Send play command from T20 to ASE product.
      -> playback should resumed
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PAUSE_STATE)
    time.sleep(10)
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)

  def remote_control_standby_when_playback_is_active(self):
    """ Verify volume up/down on ASE product when playback is active using  T20 remote

    Precondition:
      - Playback is active on ASE product
    Steps:
      1. Send standby command from T20 remote.
      -> Verify product is in standby using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self.tal_http.power_state_standby_standby()
    time.sleep(5)
    if self.tal_http.get_power_state() != "standby":
      raise TestAssertionError("The board is not in standby")

  def remote_control_standby_when_in_multiroom_session(self):
    """ Verify standby on ASE product when product is in multiroom session.

    Precondition:
      - Product A is a leader of Product B in a multiroom session.
    Steps:
      1. Send standby command to product A from T20 remote.
      -> Verify no sound from the Leader
      -> Verify playback status of product B is play.
    Hyperion::
      @Role1: Leader
      @Role2: Follower
      @Equipment: [sound_card]
    """
    self._verify_playback_status_multiroom(self.leader, comm_const.PLAY_STATE)
    time.sleep(10)
    self._join(self.follower)
    time.sleep(60)
    self.follower.tal_http.start_listening_to_notifications(200)
    self._standby_and_verify(self.leader)
    self.leader.sound_verification.verify_no_sound(True)
    self._verify_playback_status_multiroom(self.follower, comm_const.PLAY_STATE)

  def remote_control_all_standby_when_product_is_standby(self):
    """Verify ALL standby using T20 one product is in standby.

    Precondtion:
      -Local playback may/may not active on the product B.
      -Product A is in standby mode.
    Steps:
      1. Send All Standby command to product A from T20 remote
      -> Verify that all the products should enter to standby
    """
    """
    self._verify_playback_status_multiroom(self.follower, comm_const.PLAY_STATE)
    self._standby_and_verify(self.leader)
    self._standby_and_verify(self.leader, standby=False)
    """
    raise NotImplementedError

  def remote_control_all_standby_when_product_is_active(self):
    """Verify ALL standby using T20 one product is standby

    Precondtion:
      -Local playback may/may not active on the product B.
      -Playback is active on product A
    Steps:
      1. Send All Standby command to product A from T20 remote
      -> Verify that all the products should enter to standby
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    """
    self._verify_playback_status_multiroom(self.leader, comm_const.PLAY_STATE)
    self._verify_playback_status_multiroom(self.follower, comm_const.PLAY_STATE)
    self._standby_and_verify(self.leader,standby=False)
    """
    raise NotImplementedError

  def remote_control_all_standby_when_product_is_leader(self):
    """Verify ALL standby using T20 one product is standby

    Precondtion:
      -Local playback may/may not active on the product B.
      -Product A is a leader of Product B in a multiroom session
    Steps:
      1. Send All Standby command to product A from T20 remote
      -> all the products should enter to standby
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    """
    self._verify_playback_status_multiroom(self.leader, comm_const.PLAY_STATE)
    self._join(self.follower)
    time.sleep(60)
    self._standby_and_verify(self.leader,standby=False)
    """
    raise NotImplementedError

  def remote_control_all_standby_when_product_is_follower(self):
    """Verify ALL standby using T20 one product is standby

    Precondtion:
      -Local playback may/may not active on the product B.
      -Product A is a follower of Product B in a multiroom session
    Steps:
      1. Send All Standby command to product A from T20 remote
      -> all the products should enter to standby
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    """
    self.leader.nav_ltap.target.set_IR_telegram_format_F0()
    self.follower.nav_ltap.target.set_IR_telegram_format_F0()
    self.follower.tal_http.stream_play()
    time.sleep(10)
    self._join(self.leader)
    self._standby_and_verify(self.leader,standby=False)
    """
    raise NotImplementedError

  def remote_control_volume_up_down_when_playback_is_mute(self):
    """ Verify volume up/down on ASE product when playback is active using T20 remote

    Precondition:
      - Playback is mute on ASE product
    Steps:
      1. Send volume up/down command from T20 remote.
      -> Verify playback is unmuted using BNR
    """
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    time.sleep(10)
    self.nav_ltap.mute()
    time.sleep(10)
    self.nav_ltap.volume_up()
    time.sleep(5)
    self._mute_or_unmute_verify(is_muted=False)

  def remote_control_join_when_product_is_standby(self):
    """Verify join operation  on ASE product using T20 remote

    Precondtions:
      - Playback is active on product B
      - Product A is in standby mode
    Steps:
      1. Send Join command to product A from T20 remote and verify the playback
      -> Product A should join the playback of Product B.
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self._verify_playback_status_multiroom(self.follower, comm_const.PLAY_STATE)
    self._standby_and_verify(self.leader)
    time.sleep(20)
    self.leader.nav_ltap.cd2()
    time.sleep(20)
    self._verify_active_source_playback(self.leader, self.follower)

  def remote_control_join_when_product_is_active(self):
    """Verify join operation  on ASE product using T20 remote

    Precondtions:
      - Playback is active on product B
      - Playback is active on product A
    Steps:
      1. Send Join command to product A from T20 remote remote and verify the playback
      -> Current playback should get interrupted from joined experience. Product A should join the playback of Product B.
    Hyperion::
      @Role1: Leader
      @Role2: Follower
    """
    self.follower.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    play_ids = self.follower._deezer_client.add_tracks_to_play_queue(1)
    time.sleep(10)
    self.follower.tal_http.play_queue_play(play_ids[0])
    time.sleep(10)
    self._verify_playback_status_multiroom(self.leader, comm_const.PLAY_STATE)
    time.sleep(10)
    self.leader.nav_ltap.cd2()
    time.sleep(20)
    self._verify_active_source_playback(self.leader, self.follower)

  def remote_control_different_product_options_using_beo4(self):
    """ Verify different option on ASE product.

    Precondition:
      - Option is set on ASE product.
    Steps:
      1. Set Option 0.
      -> Verify play/pause, next/preivous is not working.
    """
    """
    self._set_option_programming(self.leader,0)
    self._play_or_pause_and_verify(comm_const.PLAY_STATE)
    self._next_and_previous_and_verify()
    """
    raise NotImplementedError

# if __name__ == "__main__":
#   """ """
#   #===============================================================================
#   # # creation of an xml file with test cases
#   #===============================================================================
#   import sys
#   from Common.src.Helpers import create_tc_creator_xml_file, update_tc_xml_file
# #  output_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/TestCasesCreate.xml"
# #  create_tc_creator_xml_file(sys.modules[__name__], output_file)
#   input_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/RemoteControl_tc.xml"
#   start_path = "/home/vsu/svn/beotest/Trunk/products"
#   update_tc_xml_file(sys.modules[__name__], input_file, start_path)

#   # integration test
#   from BTE.src.TestRunner import BeoTestRunner
#   from BTE.src.CommonTestClasses import BeoTestResult
#
#   test_case_arguments = ""
#   result = BeoTestResult()
#   target_name = {"ASE_EZ2": {}}
#   test_id = None
#   test_module_name = "ASE.src.RemoteControl"
#   test_class_name = "RemoteControlIR"
#   test_case_name = "t20_pause_play"
# #   test_case_name = "linein_starts_playing_automatically"
#   # test_case_name = "linein_playing_within_3min_timeout_no_other_sources"
#   # test_case_name = "linein_playing_over_3min_timeout_no_other_sources"
#   # test_case_name = "linein_playing_over_3min_timeout_another_source"
#   # test_case_name = "linein_dropped_source_within_10sec"
#   # test_case_name = "linein_dropped_source_over_10sec"
#   # test_case_name = "linein_sense_timer_within_10sec_another_source"
#   # test_case_name = "linein_sense_timer_within_10sec_no_other_sources"
#   # test_case_name = "linein_sense_timer_over_10sec_another_source"
#   # test_case_name = "linein_sense_timer_over_10sec_no_other_sources"
#   # test_case_name = "linein_switch_from_another_source_to_linein_and_back"
#   # test_case_name = "linein_switch_from_to_another_source_automatically_many_times"
#   # test_case_name = "linein_start_stop_play_many_times"
#   # test_case_name = "linein_play_for_long_time"
#   test_case_known_error = None
#   test_case_setup = None
#   test_case_script = None
#   test_case_cleanup = None
#
#   tr = BeoTestRunner(result, target_name, test_id, test_module_name, test_class_name, test_case_name, test_case_arguments,
#                      test_case_setup, test_case_script, test_case_cleanup, local_run=False)
#   tr.run()
