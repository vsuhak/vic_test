"""
  Test Design for the component: Source Change

  @copyright: 2015 Bang & Olufsen A/S
  @organization: Bang & Olufsen A/S
  @author: TCS-RUG
"""
import time
from datetime import datetime, timedelta
import random

import ASE.src.Helpers as ASEHelpers
import Common.src.Constants as comm_const
import Common.src.Helpers as Helpers
from BTE.src.CommonTestClasses import BeoTestClass
from BTE.src.CustomExceptions import TestAssertionError
from Common.src.ITunes import ITunesState
import Common.ASE.CommonLib.src.PlayBack as PlayBack


class SourceChange(BeoTestClass):
  """Class for testing changing of the sources """
  _FREQUENCY = 1100
  _LINE_IN_PLAY_DURATION = 30
  _BLUETOOTH_FREQUENCY = 800
  _BLUETOOTH_PLAY_DURATION = 30
  _LINE_IN_PAUSE_TIME = 180  # 3 min
#   # Settings for debugging
#   _MANY_TIMES = 10
#   _LONG_TIME_AIR_PLAY = (10 * 60)  # 10 minutes
  # Settings for testing
  _MANY_TIMES = 100
  _LONG_TIME_AIR_PLAY = (1 * 60 * 60)  # 1 hour

  # pylint:disable=E1101
  def setUp(self):
    """
    Setup
    """
    self.tal_http.debug = True
    if self.sound_card:
      Helpers.mute_sound_output(self.sound_card)
      self._linein = PlayBack.LineInCommands(self.tal_http, self.logger, self.sound_card)

    self._sound_verification = ASEHelpers.SoundVerification(self.logger,
                                                            self.sound_card,
                                                            self.tal_http,
                                                            self.assertFalse,
                                                            self.assertEqual,
                                                            55)

    if self.bt_sound_card:
      self._bluetooth = PlayBack.BlueToothCommands(self.tal, self.tal_http, self.logger, self.bt_sound_card)

      # connecting BT player if it is necessary
      if len(self.tal_http.get_bluetooth_devices()) == 0:
        self._bluetooth.pair(self.tal.bluetooth_mac_address)

    ASEHelpers.check_tunein_url(self.tal, self.tal_http, self.selenium_server, self.chromecast, self.skipTest)

    self._deezer_account = ASEHelpers.get_deezer_account(self.tal)
    self._tunein_account = comm_const.TUNEIN_ACCOUNT

    self._deezer_client = ASEHelpers.DeezerClientHelper(self.tal_http, self.logger, self._deezer_account, self.skipTest)
    self._tunein_client = ASEHelpers.TuneInClientHelper(self.tal_http, self.logger, self._tunein_account, self.skipTest, self.tal)

    self._dlna_client = ASEHelpers.DLNAClientHelper(self.tal_http, self.logger)

    self._streaming = PlayBack.StreamingCommands(self.tal_http, self.logger)
    self._play_queue = PlayBack.PlayQueue(self.tal_http, self.logger)

    if self.apple_communicator is not None:
      self.apple_communicator.ip_address = self.tal.get_ip()
      self.apple_communicator.create_client(60)
    self._verification = ASEHelpers.Verification(self.logger,
                                                 self.tal_http,
                                                 self.assertFalse,
                                                 self.assertEqual)
    self.product_friendly_name = self.tal_http.get_product_friendly_name()
    self._play_queue.clear()
    self._linein_stop_time = 0

    ASEHelpers.run_first_time_setup(self.tal, self.tal_http, self.selenium_server, self.chromecast)

    self.setUp_done()

  def tearDown(self):
    """
    Tear down
    """
    self.tearDown_starts()

    self._streaming.stop(0)
    if self.sound_card:
      self._linein.stop(0)
      Helpers.mute_sound_output(self.sound_card)
    if self.bt_sound_card:
      self._bluetooth.stop(0)
      self._bluetooth.disconnect(self.tal.bluetooth_mac_address)

    # common waiting time for all sound sources
    waiting_time = 5
    self.logger.info("Waiting for no sound on output: %s seconds." % waiting_time)
    time.sleep(waiting_time)

  def _linein_play(self):
    """
    Method will first change the source of ASE to line-in then start playing.
    """
    # checking if 3 min from the last line-in play have passed
    linein_pause_time = self._LINE_IN_PAUSE_TIME - (time.time() - self._linein_stop_time)
    if linein_pause_time > 0:
      self.logger.info("Sleeping %s sec to enable line-in" % linein_pause_time)
      time.sleep(linein_pause_time)

    self.logger.info("Start playing line-in")
    Helpers.unmute_sound_output(self.sound_card)

    self._linein.play_frequency(self._FREQUENCY, self._LINE_IN_PLAY_DURATION)
    self._verification.verify_active_source(comm_const.Source.LINEIN)

  def _linein_verify(self):
    """
    Method will verify the sound frequency on line-in.
    """
    self.logger.info("Verifying playing line-in")
    self._sound_verification.verification_volume_level = 50
    self._sound_verification.verify_frequency(self._FREQUENCY)
    self._linein.stop()
    self._linein_stop_time = time.time()

  def _linein_play_and_verify(self):
    """
    Method will first play line-in and then verify the sound frequency.
    """
    self._linein_play()
    self._linein_verify()

  def _bluetooth_play(self):
    """ This method will start playing via the bluetooth connection.
    """
    self.logger.info("Connecting Bluetooth")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.BLUETOOTH)
    self._bluetooth.connect(self.tal.bluetooth_mac_address)
    Helpers.unmute_sound_output(self.sound_card)
    self.logger.info("Start playing Bluetooth")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.BLUETOOTH)
    self._bluetooth.play_frequency(self._BLUETOOTH_FREQUENCY, self._BLUETOOTH_PLAY_DURATION, 10)
    self._verification.verify_active_source(comm_const.Source.BLUETOOTH)

  def _bluetooth_verify(self):
    """ Methods will verify playing via the bluetooth connection.
    """
    self.logger.info("Verifying playing Bluetooth")
    self._sound_verification.verification_volume_level = 50
    self._sound_verification.verify_frequency(self._BLUETOOTH_FREQUENCY)

    self._bluetooth.stop()
    self._bluetooth.disconnect(self.tal.bluetooth_mac_address)

  def _bluetooth_play_and_verify(self):
    """ Methods will connect play and verify playing via the bluetooth connection.
    """
    self._bluetooth_play()
    self._bluetooth_verify()

  def _dlna_track_add_and_play(self):
    """ This method will add a DLNA track in play queue and play it
    """
    self._dlna_client.play_track(self.dlna_server.URL_FREQ_DLNA1[0], 10)
    self._verification.verify_active_source(comm_const.Source.MUSIC)

  def _dlna_track_verify(self):
    """ This method will verify a DLNA track is playing.
    """
    self.logger.info("Verifying playing DLNA")
    self._sound_verification.verification_volume_level = 50
    self._verification.verify_playback(self._sound_verification,
                                       self.dlna_server.URL_FREQ_DLNA1[1])
    self.logger.info("Stop playing DLNA")
    self._stop_stream()

  def _dlna_track_add_play_and_verify(self):
    """ Method adds a DLNA track and verify whether its added or not
    then starts playing the track and verify whether the track is playing or not
    """
    self._dlna_track_add_and_play()
    self._dlna_track_verify()

  def _deezer_track_add_and_play(self):
    """ This method will add a Deezer track in play queue and play it.

    @return: Returns the play id's added to the play queue.
    @rtype: list of strings
    """
    if not self._deezer_client.is_logged_in():
      self.logger.info("Logging in to Deezer")
      self._deezer_client.logout()
      time.sleep(3)  # Needs a little time between logout and login.
      self._deezer_client.login()

    self.logger.info("Start playing Deezer")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.DEEZER)
    play_ids = self._deezer_client.add_tracks_to_play_queue(1)
    self.tal_http.play_queue_play(play_ids[0])
    self._verification.verify_active_source(comm_const.Source.DEEZER)
    return play_ids

  def _deezer_track_verify(self, play_id):
    """ Method verifies whether the specified track is playing or not.
    """
    self.logger.info("Verifying playing Deezer")
    play_now_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(play_id, play_now_id, "Track did not start playing")
    time.sleep(5)  # Needs a little time
    self._verification.verify_playback(self._sound_verification)
    self.logger.info("Stop playing Deezer")
    self._stop_stream()

  def _deezer_track_add_play_and_verify(self):
    """ Method adds a Deezer track and starts playing the track
    and verify whether the track is playing or not.
    """
    play_ids = self._deezer_track_add_and_play()
    self._deezer_track_verify(play_ids[0])

  def _tunein_station_play(self, play_id):
    """ This method will start playing a TuneIn station from the play queue.

    @param play_id: Specifies the play id to start playing.
    @type play_id: string
    """
    self.logger.info("Start playing TuneIn")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
    self.tal_http.play_queue_play(play_id)

    self._verification.verify_active_source(comm_const.Source.RADIO)

  def _tunein_station_verify(self, play_id):
    """ Method adds a TuneIn station and verify whether its added or not
    then starts playing the station and verify whether the station is playing or not

    @param play_id: Specifies the play id to verify.
    @type play_id: string
    """
    self.logger.info("Verifying TuneIn")
    play_now_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(play_id, play_now_id, "Station did not start playing")
    self._verification.verify_playback(self._sound_verification)
    self.logger.info("Stop playing TuneIn")
    self._stop_stream()

  def _tunein_station_play_and_verify(self, play_id):
    """ Method starts playing a TuneIn station and verifies whether the station is
    playing or not.

    @param play_id: Specifies the play id to start playing.
    @type play_id: string
    """
    self._tunein_station_play(play_id)
    time.sleep(5)  # Needs a little time
    self._tunein_station_verify(play_id)

  def _itunes_play_and_verify(self, itunes_stop=True):
    """ Method will play iTunes and verify the play state and active source
    """
    if self.apple_communicator is not None:
      self.logger.info("Start playing iTunes")
      hres = self.apple_communicator.execute_apple_script('%s "%s"' % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                                       self.product_friendly_name))
      self.logger.info("the apple script '%s' returns %s" % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                             hres))
      if hres != ['0']:
        raise TestAssertionError("Cannot select speakers")
      self.apple_communicator.itunes_set_volume(60)
      self.apple_communicator.itunes_start_play_music()
      ASEHelpers.test_timeout(self.logger, 10, "Playing iTunes")

      self.logger.info("Verifying playing iTunes")
      playstate = self.apple_communicator.itunes_get_play_state()
      self.logger.info("iTunes play state is: '%s'" % playstate)
      if ITunesState.PLAYING != playstate:
        raise TestAssertionError("iTunes is not playing")
      self._verification.verify_active_source(comm_const.Source.AIRPLAY)
      if itunes_stop:
        self.apple_communicator.itunes_select_computer_speaker()
        self.apple_communicator.itunes_stop()
    else:
      self.logger.info("There is no 'apple_communicator' in the system. Skipping iTunes")

  def _stop_stream(self):
    """it stops playing the stream
    """
    active_source = self.tal_http.get_active_sources()
    self.logger.info("active source: %s" % active_source)
    if active_source["primary"] and active_source["primary"] != comm_const.Source.LINEIN:
      self._streaming.stop()

  def _speaker_mute(self, delay=5):
    """ Mutes the speaker output on the DUT.

    @param delay: Specifies the delay before no sound on output.
    @type delay: unsigned integer
    """
    self.logger.info("Muting the speaker")
    self.tal_http.speaker_mute()
    if delay > 0:
      self.logger.info("Waiting for no sound on output: %s seconds." % delay)
      time.sleep(delay)

  def _source_change(self, play_id):
    """ Method for changing source: line-in - Bluetooth - DLNA - Deezer - TuneIn
    2.10 Last User Wins

    @todo: Add ITunes to the list of sources

    Steps:
      1. start playing on line-in
        -> verify that sound comes out from speakers
      2. start playing on Bluetooth
        -> verify that sound comes out from speakers
      4. Start playing the track
        -> verify that the sound comes out of speakers
      5. Add a Deezer track into play queue.
      6. Start playing the track.
        -> Verify whether the same track is playing or not using BeoNetRemote.
      7. Add a TuneIn station into play queue.
      8. Start playing the station.
        -> Verify whether the same station is playing or not using BeoNetRemote.


    @param play_id: Specifies the play id to use in test.
    @type play_id: string

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    self._linein_play_and_verify()

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play_and_verify()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

    self._dlna_track_add_play_and_verify()

    self._deezer_track_add_play_and_verify()

    self._tunein_station_play_and_verify(play_id)

  def _source_change_light(self, play_id):
    """ Method for changing source: DLNA - Deezer - TuneIn
    2.10 Last User Wins

    Steps:
      1. Start playing the track
        -> verify that the sound comes out of speakers
      2. Add a Deezer track into play queue.
      3. Start playing the track.
        -> Verify whether the same track is playing or not using BeoNetRemote.
      4. Add a TuneIn station into play queue.
      5. Start playing the station.
        -> Verify whether the same station is playing or not using BeoNetRemote.

    @param play_id: Specifies the play id to use in test.
    @type play_id: string
    """
    self._dlna_track_add_play_and_verify()
    self._deezer_track_add_play_and_verify()
    self._tunein_station_play_and_verify(play_id)

  def _parse_arguments_stress_tests(self):
    """parse arguments for the sress test cases
    @return: a tuple (exclude_line_in, time_to_run)
    @rtype: boolean, integer

    """
    # get arguments:
    args = self.arguments.split(",")
    exclude_line_in = args[1].lower() == 'true'
    time_to_run = int(args[0].lower())
    return (exclude_line_in, time_to_run)

  def source_change(self):
    """ Check changing of source: line-in - Bluetooth - DLNA - Deezer - TuneIn
    2.10 Last User Wins
    @todo: Add ITunes to the list of sources

    Steps:
      1. start playing on line-in
        -> verify that sound comes out from speakers
      2. start playing on Bluetooth
        -> verify that sound comes out from speakers
      4. Start playing the track
        -> verify that the sound comes out of speakers
      5. Add a Deezer track into play queue.
      6. Start playing the track.
        -> Verify whether the same track is playing or not using BeoNetRemote.
      7. Add a TuneIn station into play queue.
      8. Start playing the station.
        -> Verify whether the same station is playing or not using BeoNetRemote.

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._source_change(tunein_play_ids[0])

  def source_change_stress(self):
    """ Check changing of source line-in - bluetooth - DLNA - TuneIn - Deezer for 2 hours

    Steps:
    1. repeat the test case 'test_source_change' for 2 hours.

    Hyperion::
      @ArgumentDescription:  time in min to run the test, whether the line in and bluetooth are excluded
      If True, the line in and bluetooth are excluded
      f.ex. 30,True -- execute test case 30 min, exclude line in and bluetooth
    """
    # get arguments:
    exclude_line_in, time_to_run = self._parse_arguments_stress_tests()

    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    current_time = '{:%H:%M:%S}'.format(datetime.now())
    end_time_from_now = datetime.now() + timedelta(minutes=time_to_run)
    end_time = '{:%H:%M:%S}'.format(end_time_from_now)
    self.logger.info("Starting time: %s" % current_time)
    self.logger.info("Finished time: %s" % end_time)
    test_run = 0
    while(current_time <= end_time):
      test_run += 1
      self.logger.info("Test run number: %s\n" % test_run)
      if (exclude_line_in):
        self._source_change_light(tunein_play_ids[0])
      else:
        self._source_change(tunein_play_ids[0])
      current_time = '{:%H:%M:%S}'.format(datetime.now())

  def source_change_stress_random(self):
    """Check random changing of source for 2 hours

    Steps:
    1. Change the source of ASE randomly for 2 hours
      ->Verify that changing of sources is possible

    Hyperion::
      @ArgumentDescription:  time in min to run the test, whether the line in and bluetooth are excluded
      If True, the line in and bluetooth are excluded
      f.ex. 30,True -- execute test case 30 min, exclude line in and bluetooth
    """
    # get arguments:
    exclude_line_in, time_to_run = self._parse_arguments_stress_tests()

    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    current_time = '{:%H:%M:%S}'.format(datetime.now())
    end_time_from_now = datetime.now() + timedelta(minutes=time_to_run)
    end_time = '{:%H:%M:%S}'.format(end_time_from_now)
    methods = [self._dlna_track_add_play_and_verify,
               self._deezer_track_add_play_and_verify,
               self._tunein_station_play_and_verify]

    if (not exclude_line_in):
      methods.append(self._linein_play_and_verify)

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      methods.append(self._bluetooth_play_and_verify)

    random.seed()
    self.logger.info("Starting time: %s" % current_time)
    self.logger.info("Finished time: %s" % end_time)
    test_run = 0
    while(current_time <= end_time):
      test_run += 1
      self.logger.info("Test run number: %s\n" % test_run)
      random_number = random.randint(0, len(methods) - 1)

      method_to_run = methods[random_number]
      self.logger.info("Running the method: '%s'" % method_to_run.__name__)
      if method_to_run == self._tunein_station_play_and_verify:
        method_to_run(tunein_play_ids[0])
      else:
        method_to_run()
      current_time = '{:%H:%M:%S}'.format(datetime.now())

  # ---ASE1.2
  def source_change_mute(self):
    """3.12.2 Source is muted and new source is selected

    Steps:
      1. Mute sound
      2. start playing on line-in
        -> verify that sound comes out from speakers
      3. Mute sound
      -> verify no sound
      4. start playing on BT
        -> verify that sound comes out from speakers
      5. Mute sound
      -> verify no sound
      6. Append an audio track from the DLNA to the play queue
      7. Start playing the track
        -> verify that the sound comes out of speakers
      8. Mute sound
      -> verify no sound
      9. Add a Deezer track into play queue.
      10. Start playing the track.
        -> Verify whether the same track is playing or not using BeoNetRemote.
      11. Mute sound
      -> verify no sound
      12. Add a TuneIn station into play queue.
      13. Start playing the station.
        -> Verify whether the same station is playing or not using BeoNetRemote.
      14. Mute sound
      -> verify no sound
      15. Start playing iTunes
      -> Verify whether the same station is playing or not using BeoNetRemote.

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._speaker_mute()

    self._linein_play()

    self._sound_verification.verification_volume_level = 50
    self._sound_verification.verify_frequency(self._FREQUENCY)
    self._speaker_mute()
    self._sound_verification.verify_no_sound(True)

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._sound_verification.verification_volume_level = 50
      self._sound_verification.verify_frequency(self._BLUETOOTH_FREQUENCY)
      self._speaker_mute()
      self._sound_verification.verify_no_sound(True)
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

    self._dlna_track_add_and_play()

    self._sound_verification.verification_volume_level = 50
    self._sound_verification.verify_frequency(self.dlna_server.URL_FREQ_DLNA1[1])
    self._speaker_mute()
    self._sound_verification.verify_no_sound(True)

    play_ids = self._deezer_track_add_and_play()
    play_now_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(play_ids[0], play_now_id, "Track did not start playing")
    self._sound_verification.verify_sound(True)
    self._speaker_mute()
    self._sound_verification.verify_no_sound(True)

    self._tunein_station_play(tunein_play_ids[0])
    play_now_id = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(tunein_play_ids[0], play_now_id, "Station did not start playing")
    self._sound_verification.verify_sound(True)
    self._speaker_mute()
    self._sound_verification.verify_no_sound(True)

    self._itunes_play_and_verify()

  def source_change_DLNA_can_interrupt_other_source_playback(self):
    """ Verify if playback from iOS/Android library of BeoMusic app can interrupt other source playback

    Steps:
      1. Start Playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      2. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      3. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      4. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      5. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      6. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      7. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      8. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      9. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      10. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._dlna_track_add_play_and_verify()

    self._deezer_track_add_play_and_verify()

    self._dlna_track_add_play_and_verify()

    if self.apple_communicator is not None:
      self._itunes_play_and_verify()

      self._dlna_track_add_play_and_verify()
    else:
      self.logger.info("The 'apple_communicator' is not connected. Skipping the source")

    self._linein_play()

    self._dlna_track_add_play_and_verify()

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._dlna_track_add_play_and_verify()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_deezer_can_interrupt_other_source_playback(self):
    """ Verify that Deezer playback interrupts other source playback

    Steps:
      1. Start Playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      2. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      3. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      4. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      5. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      6. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      7. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      8. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      9. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      10. Start playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._deezer_track_add_play_and_verify()

    self._dlna_track_add_play_and_verify()

    self._deezer_track_add_play_and_verify()

    if self.apple_communicator is not None:
      self._itunes_play_and_verify()

      self._deezer_track_add_play_and_verify()
    else:
      self.logger.info("The 'apple_communicator' is not connected. Skipping the source")

    self._linein_play()

    self._deezer_track_add_play_and_verify()

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._deezer_track_add_play_and_verify()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_tunein_can_interrupt_other_source_playback(self):
    """ Verify if TuneIn interrupts other source playback

    Steps:
      1. Start Playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      2. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      3. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      4. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      5. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      6. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      7. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      8. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      9. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      10. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._deezer_track_add_play_and_verify()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._dlna_track_add_play_and_verify()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    if self.apple_communicator is not None:
      self._itunes_play_and_verify()

      self._tunein_station_play_and_verify(tunein_play_ids[0])
    else:
      self.logger.info("The 'apple_communicator' is not connected. Skipping the source")

    self._linein_play()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._tunein_station_play_and_verify(tunein_play_ids[0])
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_linein_can_interrupt_other_source_playback(self):
    """ Verify if line-in playback interrupts other source playback

    Steps:

      1. Start Playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      2. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      3. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      4. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      5. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      6. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      7. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      8. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      9. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      10. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._deezer_track_add_play_and_verify()

    self._linein_play()

    self._dlna_track_add_play_and_verify()

    self._linein_play()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._linein_play()

    if self.apple_communicator is not None:
      self._itunes_play_and_verify()

      self._linein_play()
    else:
      self.logger.info("The 'apple_communicator' is not connected. Skipping the source")

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._linein_play()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_bluetooth_can_interrupt_other_source_playback(self):
    """ Verify that Bluetooth playback interrupts other source playback

    Steps:
      1. Start Playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      2. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      3. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      4. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      5. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      6. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      7. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      8. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      9. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      10. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._deezer_track_add_play_and_verify()

    self._bluetooth_play()

    self._dlna_track_add_play_and_verify()

    self._bluetooth_play()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._bluetooth_play()

    if self.apple_communicator is not None:
      self._itunes_play_and_verify()

      self._bluetooth_play()
    else:
      self.logger.info("The 'apple_communicator' is not connected. Skipping the source")

    self._linein_play()

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_airplay_can_interrupt_other_source_playback(self):
    """ Verify if AirPlay interrupts other source playback.

    Steps:
      1. Start Playing Deezer source on product
      -> Verify active source as Deezer
      -> Verify that sound comes out from speakers
      2. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      3. Start playing DLNA source on product
      -> Verify active source as DLNA
      -> Verify that sound comes out from speakers
      4. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      5. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      6. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      7. Start playing TuneIn source on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      8. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      9. Start playing line-in source on product
      -> Verify active source as line-in
      -> Verify that sound comes out from speakers
      10. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card, apple_communicator]
    """
    # prepare play queue with one radio station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)

    self._deezer_track_add_play_and_verify()

    self._itunes_play_and_verify()

    self._dlna_track_add_play_and_verify()

    self._itunes_play_and_verify()

    self._tunein_station_play_and_verify(tunein_play_ids[0])

    self._itunes_play_and_verify()

    self._linein_play()

    self._itunes_play_and_verify()

    if len(self.tal_http.get_bluetooth_devices()) > 0:
      self._bluetooth_play()

      self._itunes_play_and_verify()
    else:
      self.logger.info("Bluetooth device not connected. Skipping the source")

  def source_change_airplay_playback_for_long_duration(self):
    """Verify AirPlay playback for long duration

    Steps:
      1. start playing iTunes for for 2 hours
      -> Verify active source as Airplay
      -> Verify that sound comes out from speakers

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card, apple_communicator]
    """
    if self.apple_communicator is not None:
      self.logger.info("iTunes initiated on source")
      hres = self.apple_communicator.execute_apple_script('%s "%s"' % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                                       self.product_friendly_name))
      self.logger.info("the apple script '%s' returns %s" % (self.apple_communicator.SCRIPT_SELECT_SPEAKERS,
                                                             hres))
      if hres != ['0']:
        raise TestAssertionError("Cannot select speakers")
      self.apple_communicator.itunes_set_volume(25)
      self.apple_communicator.itunes_start_play_music()
      sleep_timeout = self._LONG_TIME_AIR_PLAY
      ASEHelpers.test_timeout(self.logger, sleep_timeout, "Playing iTunes for a long time.")
      playstate = self.apple_communicator.itunes_get_play_state()
      self.logger.info("iTunes play state is %s" % playstate)
      if ITunesState.PLAYING != playstate:
        raise TestAssertionError("iTunes is not playing")
      self._sound_verification.verify_sound(True)
      self._verification.verify_active_source(comm_const.Source.AIRPLAY)
      self.apple_communicator.itunes_select_computer_speaker()
      self.apple_communicator.itunes_stop()
      self._sound_verification.verify_no_sound(True)
    else:
      self.logger.info("There is no 'apple_communicator' in the system. Skipping iTunes")

  def source_change_toggle_playing_airplay_and_bluetooth(self):
    """ Verify if AirPlay and Bluetooth playing is able to switch many times.

    Steps:
      1. Start playing iTunes source on product
      -> Verify active source as iTunes
      -> Verify that sound comes out from speakers
      2. Start playing Bluetooth source on product
      -> Verify active source as Bluetooth
      -> Verify that sound comes out from speakers
      3. Repeat steps 1 to 2 several times.

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card, apple_communicator]
    """
    if len(self.tal_http.get_bluetooth_devices()) > 0:
      for test_run in range(self._MANY_TIMES):
        self.logger.info("Test run number: %s\n" % (test_run + 1))

        self._bluetooth_play_and_verify()

        self._itunes_play_and_verify()
    else:
      error_message = "Bluetooth device not connected. Skipping the test"
      self.logger.info(error_message)
      self.skipTest(error_message)

  def source_change_tunein_playing_change_to_same_station(self):
    """ Verify if playing a TuneIn station continues when changing to same station in the play queue.

    Trying to recreate following message in syslog:
    ....Ignored attempt to play the same live stream

    Steps:
      1. Add same TuneIn station to play queue twice.
      2. Start playing the TuneIn station on product
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      3. Set the play pointer to the next (same) TuneIn station in the queue.
      -> Verify active source as TuneIn
      -> Verify that sound comes out from speakers
      -> Verify the play pointer keeps pointing to the initial play id.

    Hyperion::
      @Role: SoundDetector
      @Equipment: [sound_card, bt_sound_card]
    """
    # start playing the TuneIn station
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)
    play_id_first = tunein_play_ids[0]
    self._tunein_station_play_and_verify(play_id_first)

    # add same TuneIn station to queue
    tunein_play_ids = self._tunein_client.add_stations_to_play_queue(1)
    play_id_second = tunein_play_ids[0]
    time.sleep(5)
    self.logger.info("Start playing TuneIn")
    self.tal_http.set_active_source(comm_const.SourceJidPrefix.RADIO)
    self.logger.info("Start playing same station with new play id: '%s'" % play_id_second)
    self.tal_http.set_play_pointer(play_id_second)
    time.sleep(5)
    self.logger.info("Verifying the initial play id is still playing.")
    play_id_now = self.tal_http.get_play_queue_playnowid()
    self.assertEqual(play_id_now, play_id_first, "The item '%s' did not keep playing." % play_id_first)


if __name__ == "__main__":
  """ """
#   #===============================================================================
#   # creation of an xml file with test cases
#   #===============================================================================
#   import sys
#   from Common.src.Helpers import create_tc_creator_xml_file, update_tc_xml_file
# #   output_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/TestCasesCreate.xml"
# #   create_tc_creator_xml_file(sys.modules[__name__], output_file)
#   input_file = "/home/vsu/svn/beotest/Trunk/products/ASE/xml/AnalogLineIn_tc.xml"
#   start_path = "/home/vsu/svn/beotest/Trunk/products"
#   update_tc_xml_file(sys.modules[__name__], input_file, start_path)
#
  # integration test
  from BTE.src.TestRunner import BeoTestRunner
  from BTE.src.CommonTestClasses import BeoTestResult

  test_case_arguments = ""
  result = BeoTestResult()
  target_name = {"ASE_A9": {}}
  test_id = None
  test_module_name = "ASE.src.SourceChange"
  test_class_name = "SourceChange"

  test_case_name = "source_change"
#   test_case_name = "source_change_for_2_hours"
#   test_case_name = "source_change_for_2_hours_random"
#   test_case_name = "source_change_mute"
#   test_case_name = "source_change_DLNA_can_interrupt_other_source_playback"
#   test_case_name = "source_change_deezer_can_interrupt_other_source_playback"
#   test_case_name = "source_change_tunein_can_interrupt_other_source_playback"
#   test_case_name = "source_change_linein_can_interrupt_other_source_playback"
#   test_case_name = "source_change_bluetooth_can_interrupt_other_source_playback"
#   test_case_name = "source_change_airplay_can_interrupt_other_source_playback"
#   test_case_name = "source_change_airplay_playback_for_long_duration"
#   test_case_name = "source_change_toggle_playing_airplay_and_bluetooth"
#   test_case_name = "source_change_tunein_playing_change_to_same_station"

  test_case_known_error = None
  test_case_setup = None
  test_case_script = None
  test_case_cleanup = None

  tr = BeoTestRunner(result, target_name, test_id, test_module_name, test_class_name, test_case_name, test_case_arguments,
                     test_case_setup, test_case_script, test_case_cleanup, local_run=False)
  tr.run()
