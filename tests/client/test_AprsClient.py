import unittest
import unittest.mock as mock

from ogn.parser import parse
from ogn.client.client import create_aprs_login, AprsClient
from ogn.client.settings import APRS_APP_NAME, APRS_APP_VER


class AprsClientTest(unittest.TestCase):
    def test_create_aprs_login(self):
        basic_login = create_aprs_login('klaus', -1, 'myApp', '0.1')
        self.assertEqual('user klaus pass -1 vers myApp 0.1\n', basic_login)

        login_with_filter = create_aprs_login('klaus', -1, 'myApp', '0.1', 'r/48.0/11.0/100')
        self.assertEqual('user klaus pass -1 vers myApp 0.1 filter r/48.0/11.0/100\n', login_with_filter)

    def test_initialisation(self):
        client = AprsClient(aprs_user='testuser', aprs_filter='')
        self.assertEqual(client.aprs_user, 'testuser')
        self.assertEqual(client.aprs_filter, '')

    @mock.patch('ogn.client.client.socket')
    def test_connect_full_feed(self, mock_socket):
        client = AprsClient(aprs_user='testuser', aprs_filter='')
        client.connect()
        client.sock.send.assert_called_once_with('user testuser pass -1 vers {} {}\n'.format(
                                                 APRS_APP_NAME, APRS_APP_VER).encode('ascii'))
        client.sock.makefile.assert_called_once_with('rw')

    @mock.patch('ogn.client.client.socket')
    def test_connect_client_defined_filter(self, mock_socket):
        client = AprsClient(aprs_user='testuser', aprs_filter='r/50.4976/9.9495/100')
        client.connect()
        client.sock.send.assert_called_once_with('user testuser pass -1 vers {} {} filter r/50.4976/9.9495/100\n'.format(
                                                 APRS_APP_NAME, APRS_APP_VER).encode('ascii'))
        client.sock.makefile.assert_called_once_with('rw')

    @mock.patch('ogn.client.client.socket')
    def test_disconnect(self, mock_socket):
        client = AprsClient(aprs_user='testuser', aprs_filter='')
        client.connect()
        client.disconnect()
        client.sock.shutdown.assert_called_once_with(0)
        client.sock.close.assert_called_once_with()
        self.assertTrue(client._kill)

    def test_reset_kill_reconnect(self):
        client = AprsClient(aprs_user='testuser', aprs_filter='')
        client.connect()

        # .run() should be allowed to execute after .connect()
        mock_callback = mock.MagicMock(
            side_effect=lambda raw_msg: client.disconnect())

        self.assertFalse(client._kill)
        client.run(callback=mock_callback, autoreconnect=True)

        # After .disconnect(), client._kill should be True
        self.assertTrue(client._kill)
        self.assertEqual(mock_callback.call_count, 1)

        # After we reconnect, .run() should be able to run again
        mock_callback.reset_mock()
        client.connect()
        client.run(callback=mock_callback, autoreconnect=True)
        self.assertEqual(mock_callback.call_count, 1)

    def test_50_live_messages(self):
        print("Enter")
        self.remaining_messages = 50

        def process_message(raw_message):
            if raw_message[0] == '#':
                return
            try:
                message = parse(raw_message)
                print("{}: {}".format(message['beacon_type'], raw_message))
            except NotImplementedError as e:
                print("{}: {}".format(e, raw_message))
                return
            if self.remaining_messages > 0:
                self.remaining_messages -= 1
            else:
                raise KeyboardInterrupt

        client = AprsClient(aprs_user='testuser', aprs_filter='')
        client.connect()
        try:
            client.run(callback=process_message, autoreconnect=True)
        except KeyboardInterrupt:
            pass
        finally:
            client.disconnect()
        self.assert_(True)
