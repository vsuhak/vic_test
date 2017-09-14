"""
  Test Design for 'Sound Volume' use cases

  @copyright: 2015 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: TCS-RUG
"""

import time

import ASE.src.Helpers as ASEHelpers
import Common.src.Constants as comm_const
import Common.src.Helpers as Helpers
from BTE.src.CommonTestClasses import BeoTestClass
import Common.ASE.CommonLib.src.Constants as ase_const
from BTE.src.CustomExceptions import TestAssertionError


class SoundVolume(BeoTestClass):
  """Class for testing sound volume and other different 'sound volume'
  cases for all sources

  Test cases should be repeated for all available sources
  """
  _TIMEDELAY_TWO_SECONDS = 2
  _TIMEDELAY_THREE_SECONDS = 3

  # pylint:disable=E1101
  def setUp(self):
    """
    Setup
    """
    self.tal_http.debug = True
    if self.sound_card:
      Helpers.mute_sound_output(self.sound_card)
    self._sound_verification = ASEHelpers.SoundVerification(self.logger, self.sound_card, self.tal_http, self.assertFalse, self.assertEqual)
    self._verification = ASEHelpers.Verification(self.logger,
                                                 self.tal_http,
                                                 self.assertFalse,
                                                 self.assertEqual)

    self._deezer_account = ASEHelpers.get_deezer_account(self.tal)
    self._deezer_client = ASEHelpers.DeezerClientHelper(self.tal_http, self.logger, self._deezer_account, self.skipTest)

    ASEHelpers.check_tunein_url(self.tal, self.tal_http, self.selenium_server, self.chromecast)
    self._tunein_account = comm_const.TUNEIN_ACCOUNT

    self._tunein_client = ASEHelpers.TuneInClientHelper(self.tal_http, self.logger, self._tunein_account, self.skipTest, self.tal)

    self._dlna_client = ASEHelpers.DLNAClientHelper(self.tal_http, self.logger)
    Helpers.clear_queue(self.tal_http)

    # On V200 sound volumes cannot be changed when in standby
    if self.tal_http.product_id.type_number in comm_const.ProductType.V200_TYPE_LIST:
      self.tal_http.set_active_source(comm_const.SourceJidPrefix.LINEIN)
      self._verification.verify_active_source(comm_const.SourceJidPrefix.LINEIN, get_ids=True)

    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self.setUp_done()

  def tearDown(self):
    """
    Tear down
    """
    self.tearDown_starts()
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_90)
    if self.sound_card:
      res = self.sound_card.stop()
      self.logger.info("stopping sound_card. Result: %s" % res)
      self.logger.info("stopping sound_card")
      Helpers.mute_sound_output(self.sound_card)
    self.tal_http.stream_stop()

  def _play_verify_dlna(self):
    """Play DLNA source and verify using BNR
    """
    self.logger.info("Start DLNA and verify playback")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    self.tal_http.start_listening_to_notifications(30)
    self._dlna_client.play_track(self.dlna_server.URL_DLNA)
    result = self.tal_http.wait_for_notification(ase_const.PROGRESS_INFORMATION_NOTIFICATION, 20, 0, "state", comm_const.PLAY_STATE)
    if not result:
      raise TestAssertionError("expected notification not received: '%s' with 'state': '%s'" % (ase_const.PROGRESS_INFORMATION_NOTIFICATION, comm_const.PLAY_STATE))
    self.tal_http.stop_listening_to_notifications()
    self._verification.verify_active_source(comm_const.SourceJidPrefix.MUSIC, get_ids=True)

  def _play_verify_linein(self):
    """Play LineIn source and verify using BNR
    """
    self.logger.info("Select Line In and verify playback")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.LINEIN)
    line_in_play_duration = 50
    self.sound_card.play_frequency(self._FREQUENCY, line_in_play_duration)
    time.sleep(10)
    self._verification.verify_active_source(comm_const.SourceJidPrefix.LINEIN, get_ids=True)

  def _play_verify_tunein(self):
    """Play TuneIn source and verify using BNR
    """
    self.logger.info("Start TuneIn and verify playback")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
    play_ids = self._tunein_client.add_stations_to_play_queue(1)
    self.tal_http.play_queue_play(play_ids[0])
    time.sleep(10)
    self._verification.verify_active_source(comm_const.SourceJidPrefix.RADIO, get_ids=True)

  def _play_verify_deezer(self):
    """Play Deezer source and verify using BNR
    """
    self.logger.info("Start Deezer and verify playback")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    play_ids = self._deezer_client.add_tracks_to_play_queue(1)
    self.tal_http.play_queue_play(play_ids[0])
    time.sleep(5)
    self._verification.verify_active_source(comm_const.SourceJidPrefix.DEEZER, get_ids=True)

  def _standby_and_verify(self):
    """ Using BNR get product into standby and verify using BNR
    """
    self.logger.info("Sending standby to the product")
    self.tal_http.power_state_standby_standby()
    time.sleep(5)
    if self.tal_http.get_power_state() != comm_const.POWER_STATE_STANDBY:
      raise TestAssertionError("The product is not in standby")
    else:
      self.logger.info("The product is now in standby")

  def _pause_stream(self):
    """ Pause stream and check notifications
    """
    self.tal_http.start_listening_to_notifications(60)
    self.logger.info("Pause playback")
    self.tal_http.stream_pause()
    result = self.tal_http.wait_for_notification(ase_const.PROGRESS_INFORMATION_NOTIFICATION, 20, 0, "state", comm_const.PAUSE_STATE)
    self.tal_http.stop_listening_to_notifications()
    if not result:
      raise TestAssertionError("expected notification not received: '%s' with 'state': '%s'" % (ase_const.PROGRESS_INFORMATION_NOTIFICATION, comm_const.PAUSE_STATE))

  def _play_dlna_and_verify_volume(self, max_level, default_volume, speaker_volume):
    """ Method to play DLNA source, set maximum sound range, set default speaker volume, set speaker volume and verify
    @param max_level: level to set as maximum speaker range
    @type max_level: Integer
    @param default_volume: volume to set as default speaker level
    @type default_volume: Integer
    @param speaker_volume: volume to set as speaker volume
    @type speaker_volume: Integer
    """
    self._play_verify_dlna()
    self.logger.info("Setting max volume: %d" % max_level)
    self.tal_http.set_sound_volume_range(max_level)
    self.logger.info("Setting default volume: %d" % default_volume)
    self.tal_http.set_default_volume(default_volume)
    self.logger.info("Setting volume: %d" % speaker_volume)
    self.tal_http.set_sound_volume_level(speaker_volume)
    time.sleep(5)
    self._verification.verify_volume(speaker_volume)
    self._standby_and_verify()
    self.logger.info("Setting source: %s active" % comm_const.SourceJidPrefix.MUSIC)
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    time.sleep(10)
    self._verification.verify_active_source(comm_const.SourceJidPrefix.MUSIC, get_ids=True)
    self._verification.verify_volume(default_volume)

  def _verify_range(self, expected_volume_range):
    """To get the maximum volume range of ASE and verify the same
    @param expected_volume_range: an expected level of sound volume
    @type expected_volume_range: integer
    """
    maximum_volume_range = self.tal_http.get_sound_volume_range()
    self.assertEqual(maximum_volume_range[1], expected_volume_range, "Volume range is not set as expected")

  def _volume_change(self, level, is_increase=True):
    """To get the speaker volume level and increase or decrease the speaker volume level
    @param level: number of volume increase/decrease
    @type level: Integer
    @param is_increase: to increase or decrease
    @type is_increase: Boolean
    """
    volume_range = self.tal_http.send_http_command_get(comm_const.BEOZONE_VOLUME_SPEAKER)
    speaker_volume = volume_range[u'speaker'][u'level']
    if is_increase:
      set_volume = speaker_volume + level
    else:
      set_volume = speaker_volume - level
    self.tal_http.set_sound_volume_level(set_volume)

  def _mute_sound(self, mute=True):
    """This method will verify if the source is mute or unmute from the BNR
    @param is_muted: to verify mute/unmute
    @type is_muted: Boolean
    """
    self.tal_http.start_listening_to_notifications(30)
    if mute:
      self.logger.info("Mute Sound")
      self.tal_http.speaker_mute()
    else:
      self.logger.info("Unmute Sound")
      self.tal_http.speaker_unmute()

    result = self.tal_http.wait_for_notification(ase_const.VOLUME_NOTIFICATION, 20, 0, "speaker")
    self.tal_http.stop_listening_to_notifications()
    if not result:
      raise TestAssertionError("expected notification not received: '%s'" % ase_const.VOLUME_NOTIFICATION)
    else:
      self.logger.info("Mute state: %s" % result.data["speaker"]["muted"])
      self.assertEqual(result.data["speaker"]["muted"], mute, "Sound mute state was not correct")

  def _verify_mute_or_unmute(self, is_muted=True):
    """This method will verify if the source is mute or unmute from the BNR
    @param is_muted: to verify mute/unmute
    @type is_muted: Boolean
    """
    state_from_BNR = self.tal_http.send_http_command_get(comm_const.BEOZONE_SPEAKER_MUTED)
    sound_state = state_from_BNR[u'muted']
    if is_muted:
      self.assertTrue(sound_state, "DUT is still in unmuted state")
    else:
      self.assertFalse(sound_state, "DUT is still in muted state")

  def _verify_no_sound_from_speaker(self):
    """This method will verify that no sound is coming from speaker when speakers are muted.
    """
    channel = 2
    rec_channel = 1
    current_volume = self.sound_card.is_sound(channel, rec_channel)
    self.logger.info("current sound volume: %s" % current_volume)
    self.assertTrue(current_volume["result"], "Not passed - volume is not muted")

  def _verify_playback_status(self, playback_status):
    """ This method is to verify the playback (pause/play) status of the source
    @param playback_status: play/pause status
    """
    correct_notification_for_pause = False
    res = self.tal_http.get_notifications(30)
    for i in res:
      self.logger.info(i)
      if i.type == ase_const.PROGRESS_INFORMATION_NOTIFICATION and i.data.get('state', None) == playback_status:
        correct_notification_for_pause = True
        break
    self.assertTrue(correct_notification_for_pause, "Did not receive the %s" % ase_const.PROGRESS_INFORMATION_NOTIFICATION)

  def _verify_volume_after_standby(self, volume_diff, play_source):
    """This method is to verify the volume is set to default after standby
    @param volume_diff: Difference in volume compared to default volume
    @param play_source: Playback will be done on specified source
    """
    self.logger.info("Source to be selected %s" % play_source)
    default_before = self.tal_http.BEOZONE_VOLUME_SPEAKER_DEFAULT
    volume_before = int(default_before) + volume_diff
    self.logger.info("Start playing %s" % play_source)
    method = None
    if play_source == comm_const.Source.DLNA:
      method = self._play_verify_dlna
    elif play_source == comm_const.Source.LINEIN:
      method = self._play_verify_linein
    elif play_source == comm_const.Source.RADIO:
      method = self._play_verify_tunein
    elif play_source == comm_const.Source.DEEZER:
      method = self._play_verify_tunein
    else:
      raise TestAssertionError("Invalid source")

    method()
    self.logger.info("Set volume: %d" % volume_before)
    self.tal_http.set_sound_volume_level(volume_before)
    self._verification.verify_volume(volume_before, False)
    self._standby_and_verify()
    method()
    time.sleep(5)
    self._verification.verify_volume(default_before, True)

  # ---Sound default volume
  def sound_default_volume_increasing(self):
    """When a Product starts playing the sound volume has a default value.
    The sound volume before standby is lower than default
    Smoke test

    Steps:
      1. Play source DLNA
      2. Set maximum sound level to 70
      3. Set default sound level to 50
      4. Set the sound level to 40
      -> check sound level 40
      5. Put the product into standby
      -> check standby
      5. Start playing a source
      -> verify sound volume level 50

    Hyperion::
      @Role: ASE
    """
    self._play_dlna_and_verify_volume(ase_const.VOLUME_LEVEL_70, ase_const.VOLUME_LEVEL_50, ase_const.VOLUME_LEVEL_40)

  def sound_default_volume_decreasing(self):
    """When a Product starts playing the sound volume has a default value.
    The sound volume before standby is higher than default

    Steps:
      1. Play source DLNA
      2. Set maximum sound level to 70
      3. Set default sound level to 40
      4. Set the sound level to 50
      -> check sound level 50
      5. Put the product into standby
      -> check standby
      5. Start playing a source
      -> verify sound volume level 40

    Hyperion::
      @Role: ASE
    """
    self._play_dlna_and_verify_volume(ase_const.VOLUME_LEVEL_70, ase_const.VOLUME_LEVEL_40, ase_const.VOLUME_LEVEL_50)

  def sound_default_volume_max_absolute_volume(self):
    """If the current maximum absolute volume is lower,
    then the maximum absolute volume takes precedence

    Steps:
      1. Play source DLNA
      2. Set default sound level to 50
      2. Set maximum sound level to 40
      3. Set the sound level to 30
      -> check sound level 30
      4. Put the product into standby
      -> check standby
      5. Start playing a source
      -> verify sound volume level 40
    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set default volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_default_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_40)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_40)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_30)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_30)
    time.sleep(5)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_30)
    self._standby_and_verify()
    self.logger.info("Set source: %s active" % comm_const.SourceJidPrefix.MUSIC)
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.MUSIC)
    time.sleep(10)
    self._verification.verify_active_source(comm_const.SourceJidPrefix.MUSIC, get_ids=True)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_40)

  def sound_default_volume_max_volume(self):
    """The max sound volume when starting to play right after standby is 65

    Steps:
      1. Play source DLNA
      2. Set default sound level to 65
      2. Set maximum sound level to 70
      3. Set the sound level to 70
      -> check sound level 70
      4. Put the product into standby
      -> check standby
      5. Start playing a source
      -> verify sound volume level 65

    Hyperion::
      @Role: ASE
    """
    self._play_dlna_and_verify_volume(ase_const.VOLUME_LEVEL_70, ase_const.VOLUME_LEVEL_65, ase_const.VOLUME_LEVEL_70)

  def volume_after_standby_above_default(self):
    """Test if the volume is set to default after standby if playing above the default volume level

    Steps:
      1. Get default volume.
      2. Start playing source.
      3. Set current volume 10 above default.
      -> Verify volume is set.
      4. Put DUT in standby.
      -> Verify standby.
      5. Start playing source.
      -> Verify volume is set to default.

    Hyperion::
      @Role: ASE
    """
    raise NotImplementedError

  def volume_after_standby_below_default(self):
    """Test if the volume is set to default after standby if playing below the default volume level

    Steps:
      1. Get default volume.
      2. Start playing source.
      3. Set current volume 10 below default.
      -> Verify volume is set.
      4. Put DUT in standby.
      -> Verify standby.
      5. Start playing source.
      -> Verify volume is set to default.

    Hyperion::
      @Role: ASE
    """
    raise NotImplementedError

  # ---Sound maximum volume
  def sound_maximum_volume_set(self):
    """When playing, the sound volume of a Product cannot exceed a maximum value defined by the user.
    A user sets a volume
    Smoke test

    Steps:
      1. Play source DLNA
      2. Set a max volume to 70 (BNR)
      3. Set a sound volume to 60 using the command 'set...'
      -> check sound volume 60
      3. Set a sound volume to 75 using the command 'set...'
      -> verify sound volume 60

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    time.sleep(5)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    try:
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_75)
    except Exception as exc:
      self.logger.info("Expected error Occurred while setting speaker volume more then max %s " % exc)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)

  def sound_maximum_volume_increase_continuously(self):
    """When playing, the sound volume of a Product cannot exceed a maximum value defined by the user.
    A user increases the volume continuously
    Smoke test

    Steps:
      1. Play source DLNA
      2. Set a max volume to 70 (BNR)
      3. Set a sound volume to 65 using the command 'set...'
      -> check sound volume 65
      3. Increase sound volume continuously for 2 sec
      -> verify sound volume 70

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_65)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_65)
    time.sleep(5)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_65)
    self.logger.info("Send volume continuous up for 2 sec")
    self.tal_http.speaker_continuous_up(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_70)

  def sound_maximum_volume_absolute(self):
    """it is not possible to set max volume more than 90

    Steps:
      1. Play source DLNA
      2. Set a max volume to 91 (BNR)
      -> verify BNR exception

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    maximum_volume_range = self.tal_http.get_sound_volume_range()
    try:
      self.logger.info("Try to set volume: %d" % ase_const.VOLUME_LEVEL_91)
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_91)
    except TestAssertionError:
      maximum_volume_range_after = self.tal_http.get_sound_volume_range()
      self.assertEqual(maximum_volume_range_after[1], maximum_volume_range[1], "Volume range is set incorrectly")

  def sound_maximum_volume_set_when_playing(self):
    """A new maximum sound volume is set by the user while the Product is playing,
    the sound volume of the experience playing is louder than the setting.

    Steps:
      1. Play source DLNA
      2. Set a max volume to 70 (BNR)
      3. Set a sound volume to 60 using the command 'set...'
      -> check sound volume 60
      4. Set a max volume to 50 (BNR)
      -> verify sound volume 50

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    time.sleep(2)
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_50)
    time.sleep(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_maximum_volume_default_values(self):
    """All Products must offer the customer one or more of the following methods
    for setting the value of the maximum sound volume:
    A. A set of fixed values associated with a set of terms

    @todo: figure out whether the test valid only for web interface?

    Steps:
      1. Play source DLNA
      2. Set the max volume 'Maximum'
      -> verify max sound volume 90
      3. Set the max volume 'Loud'
      -> verify max sound volume 75
      4. Set the max volume 'Medium'
      -> verify max sound volume 60
      5. Set the max volume 'Quiet'
      -> verify max sound volume 45

    Hyperion::
      @Role: ASE
    """
    # Not possible to set the value of maximum, loud, medium, quiet from BNR using "string Values"
    # similar test cases implemented in WebInterface.py module as separate test cases
    raise NotImplementedError

  def sound_maximum_volume_custom_values(self):
    """All Products must offer the customer one or more of the following methods
    for setting the value of the maximum sound volume:
    B. Setting any value from volume 20 (minimum) to 90 (absolute maximum).

    @todo: figure out whether the test valid only for web interface?

    Steps:
      1. Play source DLNA
      2. Set the max volume 20
      -> verify max sound volume 20
      3. Set the max volume 19
      -> TBD: verify max sound volume 20 or an exception from BNR

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_20)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_20)
    time.sleep(5)
    self._verify_range(ase_const.VOLUME_LEVEL_20)
    try:
      self.logger.info("Try to set max volume: %d" % ase_const.VOLUME_LEVEL_19)
      self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_19)
    except Exception as exc:
      self.logger.info("Expected error occurred while setting speaker volume less than min %s " % exc)
    self._verify_range(ase_const.VOLUME_LEVEL_20)

  # ---Source changing
  def sound_source_change_volume_preserve(self):
    """Preserve sound volume when changing input source at a Product.
    Smoke test

    Steps:
      1. Play source DLNA
      2. Set sound volume 60
      3. Switch the source

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self._play_verify_deezer()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)

  def sound_source_change_not_playing(self):
    """The Product remembers the sound volume changing sources,
    even if the source is not playing

    Steps:
      1. Play source DLNA
      2. Set sound volume 60
      3. Switch the source, but do not start playing
      -> verify sound volume 60

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self.logger.info("Change source to Deezer")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    self.logger.info("Verify volume level is still %d" % ase_const.VOLUME_LEVEL_60)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)

  def sound_source_change_mute_not_playing(self):
    """The Product remembers the sound volume changing sources,
    when the source is not playing and muted

    Steps:
      1. Play source DLNA
      -> check the sound out of speakers
      2. Set sound volume 60
      3. Mute the sound
      4. Switch the source, but do not start playing
      -> verify sound volume 60
      -> verify sound muted

    Hyperion::
      @Role: ASE
    """
    raise NotImplementedError
    """
    self._play_verify_dlna()
    self._sound_verification.verify_sound(True)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self.tal_http.speaker_mute()
    time.sleep(10)
    self._verify_mute_or_unmute()
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    time.sleep(10)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    self._verify_mute_or_unmute()
    """

  def sound_source_change_pause_not_playing(self):
    """The Product remembers the sound volume changing sources,
    when the source is not playing and paused

    Steps:
      1. Play source DLNA
      -> check the sound out of speakers
      2. Set sound volume 60
      3. Pause the sound
      4. Switch the source, but do not start playing
      -> verify sound volume 60
      -> verify the source is paused

    Hyperion::
      @Role: ASE
    """
    raise NotImplementedError
    """
    self._play_verify_dlna()
    self._sound_verification.verify_sound(True)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self.tal_http.stream_pause()
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    time.sleep(10)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    self._sound_verification.verify_no_sound(True)
    """

  def sound_mute_remember_sound_volume(self):
    """The Product remembers the sound volume when muted

    Steps:
      1. Set the max sound volume as 70
      2. Play source DLNA.
      -> Verify that playback starts
      3. Set the volume 50
      -> check (BNR) that sound volume is 50
      4. By BNR send the command Mute
      -> verify (BNR) that sound is muted
      -> verify (BNR) that sound volume is 50
      -> verify no sound out of speakers

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Setting max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_mute_change_sound_volume_over_max(self):
    """The Product change the sound volume when muted,
    if it is higher than the max volume level
    and then it does not restore the volume level,
    if it is lower than the max volume level

    Steps:
      1. Set the max sound volume as 70
      2. Play source DLNA.
      3. Set the volume 55
      4. By BNR send the command Mute
      -> check (BNR) that sound is muted
      -> check (BNR) that sound volume is 55
      5. Set the max sound volume as 50
      -> verify (BNR) that sound volume is 55
      6. By BNR send the command Unmute
      -> check (BNR) that sound is unmuted
      -> check (BNR) that sound volume is 50
      7. Set the volume 45
      8. By BNR send the command Mute
      -> check (BNR) that sound is muted
      -> check (BNR) that sound volume is 45
      9. Set the max sound volume as 49
      -> verify (BNR) that sound volume is 45
      10. By BNR send the command Unmute
      -> check (BNR) that sound is unmuted
      -> check (BNR) that sound volume is 45

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()

    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_55)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_55)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_55)

    self.logger.info("Set max volume %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_50)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_55)
    self._mute_sound(False)
    self._verify_mute_or_unmute(False)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_45)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_45)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_45)

    self.logger.info("Set max volume %d" % ase_const.VOLUME_LEVEL_49)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_49)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_45)
    self._mute_sound(False)
    self._verify_mute_or_unmute(False)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_45)

  def sound_mute_change_sound_volume_over_60(self):
    """The maximum allowed sound volume when unmuting is volume 60

    Steps:
      1. Set the max sound volume as 80
      2. Play source DLNA.
      3. Set the volume 70
      4. By BNR send the command Mute
      -> verify (BNR) that sound is muted
      -> verify (BNR) that sound volume is 70
      5. By BNR send the command Unmute
      -> verify (BNR) that sound is unmuted
      -> verify (BNR) that sound volume is 60

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume %d" % ase_const.VOLUME_LEVEL_80)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_80)
    self._play_verify_dlna()

    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_70)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_70)
    self._mute_sound(False)
    self._verify_mute_or_unmute(False)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)

  def sound_mute_performance(self):
    """Mute the sound of a Product in 100ms

    Steps:
      1. Play source DLNA.
      -> check the sound out of speakers
      2. By BNR send the command Mute
      -> verify (BNR) that sound is muted in 100ms from the sending the 'mute' command

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Play source DLNA")
    self._play_verify_dlna()
    self.logger.info("Mute sound and verify")
    self.tal_http.speaker_mute()
    time.sleep(0.1)
    self._verify_mute_or_unmute()

  def sound_unmute_restore_sound_volume(self):
    """The Product restores the sound volume when unmuted

    Steps:
      1. Set the max sound volume as 70
      2. Play source DLNA.
      3. Set the volume 50
      4. By BNR send the command Mute
      -> check (BNR) that sound is muted
      5. By BNR send the command Unmute
      -> verify (BNR) that sound is unmuted
      -> verify (BNR) that sound volume is 50

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._mute_sound(False)
    self._verify_mute_or_unmute(False)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_unmute_sound_volume_increase(self):
    """ UnMute the sound of a Product by a sound volume control,
    increasing the sound volume

    Steps:
      1. Play source DLNA.
      -> check the sound out of speakers
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command set sound volume level with the level
      higher then the current one
      -> verify (BNR) that sound is unmuted
      -> verify sound out of speakers

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._volume_change(10)
    time.sleep(1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_decrease(self):
    """ UnMute the sound of a Product by a sound volume control,
    decreasing the sound volume

    Steps:
      1. Play source DLNA.
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command set sound volume level with the level
      lower then the current one
      -> verify (BNR) that sound is unmuted
      -> verify sound out of speakers

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._volume_change(10, False)
    time.sleep(1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_increase_continuously(self):
    """ UnMute the sound of a Product by a sound volume control,
    increasing the sound volume continuously

    Steps:
      1. Play source DLNA.
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command increase sound volume level continuously
      -> verify (BNR) that sound is unmuted

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self.logger.info("Send continuous volume up")
    self.tal_http.speaker_continuous_up()
    time.sleep(1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_decrease_continuously(self):
    """ UnMute the sound of a Product by a sound volume control,
    decreasing the sound volume continuously

    Steps:
      1. Play source DLNA.
      -> check the sound out of speakers
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command decrease sound volume level continuously
      -> verify (BNR) that sound is unmuted
      -> verify sound out of speakers

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self.logger.info("Send continuous volume down")
    self.tal_http.speaker_continuous_down()
    self._verify_mute_or_unmute(False)

  def sound_unmute_performance(self):
    """Unmute the sound of a Product in 100ms

    Steps:
      1. Play source DLNA.
      -> check the sound out of speakers
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command Unmute
      -> verify (BNR) that sound is unmuted in 100ms from the sending the 'unmute' command

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self.tal_http.speaker_unmute()
    time.sleep(0.1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_increase_performance(self):
    """Unmute the sound of a Product in 100ms by sending a command
    set volume level

    Steps:
      1. Play source DLNA.
      -> check the sound out of speakers
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command set sound volume level with the level
      higher then the current one
      -> verify (BNR) that sound is unmuted in 100ms from the sending
      the command to increase the sound volume

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._volume_change(10)
    time.sleep(0.1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_decrease_performance(self):
    """Unmute the sound of a Product in 100ms by sending a command
    set volume level

    Steps:
      1. Play source DLNA.
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command set sound volume level with the level
      lower then the current one
      -> verify (BNR) that sound is unmuted in 100ms from the sending
      the command to decrease the sound volume

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    time.sleep(10)
    self._verify_mute_or_unmute()
    self._volume_change(10, False)
    time.sleep(0.1)
    self._verify_mute_or_unmute(False)

  def sound_unmute_sound_volume_increase_continuously_performance(self):
    """Unmute the sound of a Product in 100ms by sending a command
    increase volume level continuously

    Steps:
      1. Play source DLNA.
      2. By BNR send the command Mute
      -> check (BNR) that sound is muted
      3. By BNR send the command increase sound volume level continuously
      higher then the current one
      -> verify (BNR) that sound is unmuted in 100ms from the sending
      the command to increase the sound volume

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self.logger.info("Send continuous volume up")
    self.tal_http.speaker_continuous_up(2)
    time.sleep(0.1)
    self._verify_mute_or_unmute(False)

  # ---Sound volume limit change no sound
  def sound_volume_no_sound_limit_min(self):
    """ cannot decrease a sound volume level under the min,
    if there is no sound.
    Smoke test

    Steps:
      1. No sources are played. The product is in a playing state,
      but no sound out of speakers:
      - The source is paused, or
      - Absence of signal has been detected for 10 seconds (Line-in, TOSLINK, audio streams)
      2. Set the sound volume level 30
      -> check the volume level 30
      3. Decrease sound volume level continuously for 2 sec
      -> verify the volume level is 20
      4. Set the sound volume level 30
      -> check the volume level 30
      5. Set the sound volume level 10
      -> verify the volume level is 30

    Hyperion::
      @Role: ASE
    """
    # On V200 sound volumes cannot be changed when in standby
    if self.tal_http.product_id.type_number in comm_const.ProductType.V200_TYPE_LIST:
      msg = "Test not valid for this product: %s because we can change volume when a stream is paused" % self.tal_http.product_id.type_number
      self.logger.warn(msg)
      self.skipTest(msg)

    self._play_verify_dlna()
    self._pause_stream()

    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_30)
    time.sleep(5)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_30)
    self.tal_http.speaker_continuous_down(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_20)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_30)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_30)
    try:
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_10)
    except TestAssertionError:
      self.logger.info("Expected error occurred")
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_30)

  def sound_volume_no_sound_limit_max(self):
    """ cannot increase a sound volume level under the min,
    if there is no sound.

    Steps:
      1. No sources are played. The product is in a playing state,
      but no sound out of speakers:
      - The source is paused, or
      - Absence of signal has been detected for 10 seconds (Line-in, TOSLINK, audio streams)
      2. Set the max volume level 70
      3. Set the sound volume level 30
      4. Increase sound volume level continuously for 2 sec
      -> verify the volume level is 50
      5. Set the sound volume level 30
      -> check the volume level 30
      6. Set the sound volume level 60
      -> verify the volume level is 50

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self._pause_stream()

    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_30)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_30)
    self.logger.info("Send continuous volume up for 2 sec")
    self.tal_http.speaker_continuous_up(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_30)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_30)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_30)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_volume_no_sound_limit_min_beyond(self):
    """ cannot decrease a sound volume level under the min,
    if there is no sound and current sound level is under the min

    Steps:
      1. Play the source
      2. Set the sound volume level 15
      3. Pause the source or stop a signal (Line-in, TOSLINK, audio streams) for 10 sec
      -> check the volume level is 15
      4. Decrease sound volume level continuously for 2 sec
      -> verify the volume level is 15
      5. Set the sound volume level 10
      -> verify the volume level is 15

    Hyperion::
      @Role: ASE
    """
    # On V200 sound volumes cannot be changed when in standby
    if self.tal_http.product_id.type_number in comm_const.ProductType.V200_TYPE_LIST:
      msg = "Test not valid for this product: %s because we can change volume when a stream is paused" % self.tal_http.product_id.type_number
      self.logger.warn(msg)
      self.skipTest(msg)

    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_15)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_15)
    self._pause_stream()

    self._verification.verify_volume(ase_const.VOLUME_LEVEL_15)
    self.logger.info("Send continuous volume down for 2 sec")
    self.tal_http.speaker_continuous_down(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_15)
    try:
      self.logger.info("Try to set volume: %d" % ase_const.VOLUME_LEVEL_10)
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_10)
    except TestAssertionError:
      self.logger.info("Expected error occured")
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_15)

  def sound_volume_no_sound_limit_max_beyond(self):
    """ cannot increase a sound volume level over the max,
    if there is no sound and current sound level is over the max

    Steps:
      1. Play the source
      2. Set the max volume level 70
      3. Set the sound volume level 60
      4. Pause the source or stop a signal (Line-in, TOSLINK, audio streams) for 10 sec
      -> check the volume level is 60
      5. Increase sound volume level continuously for 2 sec
      -> verify the volume level is 60
      6. Set the sound volume level 70
      -> verify the volume level is 60

    Hyperion::
      @Role: ASE
    """
    # On V200 sound volumes cannot be changed when in standby
    if self.tal_http.product_id.type_number in comm_const.ProductType.V200_TYPE_LIST:
      msg = "Test not valid for this product: %s because we can change volume when a stream is paused" % self.tal_http.product_id.type_number
      self.logger.warn(msg)
      self.skipTest(msg)

    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self._pause_stream()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    self.logger.info("Send continuous volume up for 2 sec")
    self.tal_http.speaker_continuous_up(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    try:
      self.logger.info("Try to set volume: %d" % ase_const.VOLUME_LEVEL_70)
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_70)
    except TestAssertionError:
      self.logger.info("Expected error occurred while setting speaker volume more then max")
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)

  # ---Sound volume change
  def sound_volume_continuously_up_limit(self):
    """If the user keeps changing the sound volume when it has already
    reached the limit in the direction it is changing, all further volume
    regulation commands in the same direction must be ignored.

    Steps:
      1. Set the max volume level 70
      2. Play source DLNA.
      3. Set the sound volume 50
      -> check the sound volume 50
      4. By BNR increase the sound volume level continuously for 3 sec
      -> verify (BNR) that sound level is 70
      5. By BNR increase the sound volume level continuously for 3 sec
      -> verify (BNR) that sound level is 70

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Send continuous volume up for 3 sec")
    self.tal_http.speaker_continuous_up(3)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_70)
    self.logger.info("Send continuous volume up for 3 sec")
    self.tal_http.speaker_continuous_up(3)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_70)

  def sound_volume_continuously_down_limit(self):
    """If the user keeps changing the sound volume when it has already
    reached the limit in the direction it is changing, all further volume
    regulation commands in the same direction must be ignored.

    Steps:
      1. Set the max volume level 70
      2. Play source DLNA.
      3. Set the sound volume 50
      -> check the sound volume 50
      4. By BNR decrease the sound volume level continuously for 3 sec
      -> verify (BNR) that sound level is 0
      5. By BNR decrease the sound volume level continuously for 3 sec
      -> verify (BNR) that sound level is 0
    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Send continuous volume down for 3 sec")
    self.tal_http.speaker_continuous_down(3)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_0)
    self.logger.info("Send continuous volume down for 3 sec")
    self.tal_http.speaker_continuous_down(3)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_0)

  def sound_volume_performance(self):
    """ change a sound volume level in 100ms

    Steps:
      1. Play source DLNA.
      2. By BNR send the command 'set sound level'
      -> verify (BNR) that sound level has been changed in 100ms
      from the sending the command

    Hyperion::
      @Role: ASE
    """
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    time.sleep(0.1)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_volume_full_range_up_performance(self):
    """ change a sound volume level continuously from 0 to 90 in 2sec

    Steps:
      1. Set the max volume level 90
      2. Play source DLNA.
      3. Set sound volume level to 0
      -> check the volume 0
      4. By BNR increase the sound volume level continuously for 2 sec
      -> verify (BNR) that sound level is 90

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_90)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_90)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_0)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_0)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_0)
    self.logger.info("Send continuous volume up for 2 sec")
    self.tal_http.speaker_continuous_up(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_90)

  def sound_volume_full_range_down_performance(self):
    """ change a sound volume level from 90 to 0 in 2sec

    Steps:
      1. Set the max volume level 90
      2. Play source DLNA.
      3. Set sound volume level to 90
      -> check the volume 90
      4. By BNR decrease the sound volume level continuously for 2 sec
      -> verify (BNR) that sound level is 0

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_90)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_90)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_90)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_90)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_90)
    self.logger.info("Send continuous volume down for 2 sec")
    self.tal_http.speaker_continuous_down(2)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_0)

  # ---Sound volume standby
  def sound_volume_standby_sound_volume_not_changed(self):
    """When a Product is in a standby mode, sound volume cannot be changed.
    Smoke test

    Steps:
      1. Set the max sound volume as 70
      2. Play source DLNA.
      -> check the sound out of speakers
      3. Set the volume 50
      4. By BNR send the command Standby
      -> check (BNR) that DUT is in standby
      -> check (BNR) that sound volume is 50
      5. Set the volume 40 (BNR)
      -> verify the volume 50
      6. Increase the volume
      -> verify the volume 50
      7. Decrease the volume
      -> verify the volume 50

    Hyperion::
      @Role: ASE
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_70)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_70)
    self._play_verify_dlna()
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_50)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_50)
    self.tal_http.power_state_standby_standby()
    time.sleep(5)
    if self.tal_http.get_power_state() != "standby":
      raise TestAssertionError("The board is not in standby")
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    try:
      self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_40)
    except TestAssertionError:
      self.logger.info("Expected error occurred")
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Send continuous volume up")
    self.tal_http.speaker_continuous_up()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)
    self.logger.info("Send continuous volume down")
    self.tal_http.speaker_continuous_down()
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_50)

  def sound_heard_after_unmute_volume_decreased_continuously_stopped(self):
    """ To verify that sound should come from muted DUT only when user has stopped decreasing the volume continuously.

    Steps:
      1.Start Playing source on DUT.
      2.Mute the playback on DUT.
      -> verify speaker state is muted not playback
      -> No sound from the DUT
      3.Decrease the volume continuously for 2 seconds.
      -> Verify if sound level has decreased.
      -> verify that sound from speaker should be heard only after 2 seconds.

    Hyperion::
      @Role: ASE
      @Equipment: [sound_card]
    """
    self.logger.info("Set max volume: %d" % ase_const.VOLUME_LEVEL_75)
    self.tal_http.set_sound_volume_range(ase_const.VOLUME_LEVEL_75)
    self._play_verify_dlna()
    time.sleep(5)
    self._sound_verification.verify_sound(True)
    self._mute_sound(True)
    self._verify_mute_or_unmute()
    self._sound_verification.verify_no_sound(True)
    self.logger.info("Send continuous volume down for %d sec" % self._TIMEDELAY_TWO_SECONDS)
    current_time = time.time()
    self.tal_http.speaker_continuous_down(self._TIMEDELAY_TWO_SECONDS)
    while(time.time() - current_time < 2):
      self._verify_no_sound_from_speaker()
    self._sound_verification.verify_sound(True)

  def sound_no_sound_command_accepted_in_standby(self):
    """ To verify if volume command is accepted when playback of any source is not active on DUT.

    Prerequisites:
      - No playback is active on DUT.
    Steps:
      1. Change the volume on DUT
      -> Verify the volume level has not changed

    Hyperion::
      @Role: ASE
    """
    # On V200 sound volumes cannot be changed when in standby
    if self.tal_http.product_id.type_number in comm_const.ProductType.V200_TYPE_LIST:
      msg = "Volume cannot be changed when in standby on this product"
      self.logger.warn(msg)
      self.skipTest(msg)

    volume_level_bnr = self.tal_http.get_sound_volume_level()
    self._standby_and_verify()
    self.logger.info("Send continuous volume up for %d sec" % self._TIMEDELAY_TWO_SECONDS)
    self.tal_http.speaker_continuous_up(self._TIMEDELAY_TWO_SECONDS)
    self._verification.verify_volume(volume_level_bnr)

  def sound_pause_sound_volume_over_max(self):
    """ To verify the volume level after changing the max volume range in Pause state.

    Steps:
      1. Playback is active on DUT.
      2. Set the max sound volume as "LOUD" from webpage.
      3. Set the Sound volume level at 60
      -> Verify the speaker volume level at 60.
      4. Pause the playback.
      -> Verify whether playback has been paused.
      -> check (BNR) that sound volume is 60 after pause.
      5. Set the max sound volume as "QUIET"  from webpage.
      6. Resume the playback.
      -> verify (BNR) that speaker volume is "45"

    Hyperion::
      @Role: ASE
    """
    # TO BE REMOVED!!!
    self._play_verify_dlna()
    self.logger.info("Set max volume: %d" % comm_const.VOLUME_LEVEL_LOUD)
    self.tal_http.set_sound_volume_range(comm_const.VOLUME_LEVEL_LOUD)
    self.logger.info("Set volume: %d" % ase_const.VOLUME_LEVEL_60)
    self.tal_http.set_sound_volume_level(ase_const.VOLUME_LEVEL_60)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    self._pause_stream()
    self._verify_playback_status(comm_const.PAUSE_STATE)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_60)
    self.logger.info("Set volume: %d" % comm_const.VOLUME_LEVEL_QUITE)
    self.tal_http.set_sound_volume_range(comm_const.VOLUME_LEVEL_QUITE)
    self.tal_http.stream_play()
    time.sleep(10)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_45)

  def sound_zero_sound_volume_level(self):
    """ Verify zero sound volume level
    Steps:
      1. Start playing any source on product.
      -> Verify playback on product.
      2. Decrease the volume to zero.
      -> Verify volume should be zero.
      -> Verify sound is not muted on product.

    Hyperion::
      @Role: ASE
    """
    self._play_verify_tunein()
    self._verify_playback_status(comm_const.PLAY_STATE)
    self.logger.info("Send continuous volume down for 15 sec")
    self.tal_http.speaker_continuous_down(15)
    self._verification.verify_volume(ase_const.VOLUME_LEVEL_0)
    self._verify_mute_or_unmute(is_muted=False)


if __name__ == "__main__":
  """ """
#   #===============================================================================
#   # # creation of an xml file with test cases
#   #===============================================================================
#   import sys
#   from Common.src.Helpers import create_tc_creator_xml_file, update_tc_xml_file
# #   output_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/TestCasesCreate.xml"
# #   create_tc_creator_xml_file(sys.modules[__name__], output_file)
#   input_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/SoundVolume_tc.xml"
#   start_path = "/home/vsu/svn/beotest/Trunk/products"
#   update_tc_xml_file(sys.modules[__name__], input_file, start_path)

#  integration test
  from BTE.src.TestRunner import BeoTestRunner
  from BTE.src.CommonTestClasses import BeoTestResult

  test_case_arguments = ""
  result = BeoTestResult()
  target_name = {"Apx_Testsite": {}}
  test_id = None
  test_module_name = "ASE.src.SoundVolume"
  test_class_name = "SoundVolume"

  test_case_name = "sound_mute"

  test_case_known_error = None
  test_case_setup = None
  test_case_script = None
  test_case_cleanup = None

  tr = BeoTestRunner(result, target_name, test_id, test_module_name, test_class_name, test_case_name, test_case_arguments,
                     test_case_setup, test_case_script, test_case_cleanup, local_run=False)
  tr.run()
