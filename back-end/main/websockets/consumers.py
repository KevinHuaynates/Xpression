from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from . import tests
import urllib3
import requests
from requests.auth import HTTPBasicAuth
import threading
import logging
import xmpp
import xmltodict
import datetime
import json

logging.basicConfig(level=logging.NOTSET)

class XMPPClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.server = username.split('@')[1]
        self.client = None

    def connect(self):
        jid = xmpp.protocol.JID(self.username)
        self.client = xmpp.Client(server=self.server, debug=True)
        self.client.connect()
        authenticate = self.client.auth(user=jid.getNode(), password=self.password, resource=jid.getResource())

        return authenticate

    def get_contacts(self):
        roster = self.client.getRoster()
        contacts = roster.getItems()

        return contacts

    def get_presence(self, contact_jid):
        contact_presence = ''
        def presence_handler(conn, presence):
            contact_presence = presence.getType()
            print(f'{contact_jid}: {contact_presence}')

        return contact_presence

    def send_message(self, receiver, message):
        self.client.send(xmpp.protocol.Message(to=receiver, body=message))

    def start_listener(self):
        self.thread = threading.Thread(target=self.start_listener_thread)
        self.thread.start()

    def start_listener_thread(self):
        while True:
            try:
                self.client.Process(1)  # Process incoming stanzas/events with a timeout of 1 second
            except KeyboardInterrupt:
                print("Exiting...")
                break

    def register_message_handler(self, message_handler):
        try:
            self.client.RegisterHandler('message', message_handler)
            logging.info("Message handler registered successfully.")
        except Exception as exception:
            logging.error(f"Failer to register message handler: {exception}")

    def logout(self):
        if self.client:
            self.client.disconnect()

class LoginConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()
        self.send(text_data=json.dumps({
            'type': 'connection_stablished',
            'message': 'You are now connected!'
        }))

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        print(text_data_json)
        if 'type' not in text_data_json:
            self.send(json.dumps({
                'success': False,
                'message': 'Bad request'
            }))
            
        if text_data_json['type'] == 'login_request':
            username = text_data_json['username']
            password = text_data_json['password']

            print('username:', username)
            print('password:', password)

            logging.info("mensaje")
            logging.info(f"password: {password}")

            self.xmpp_client = XMPPClient(username, password)
            authenticate = self.xmpp_client.connect()

            contacts = self.xmpp_client.get_contacts()

            if authenticate == 'sasl':
                self.xmpp_client.client.sendInitPresence()
                self.send(json.dumps({
                    'success': True,
                    'message': 'Log in successful'
                }))
                self.xmpp_client.register_message_handler(self.message_handler)
                self.xmpp_client.start_listener()
            
        elif text_data_json['type'] == 'get_roster':
            print(text_data_json)
            self.send_roster()

        elif text_data_json['type'] == 'get_presence':
            print(text_data_json)
            contact_jid = xmpp.protocol.JID(text_data_json['user'])
            self.get_presence(contact_jid)

        elif text_data_json['type'] == 'send_message':
            receiver = text_data_json['to']
            message = text_data_json['message']
            utc_now = datetime.datetime.utcnow()
            local_time_difference = datetime.timedelta(hours=-5)
            local_time_now = utc_now + local_time_difference
            current_time = local_time_now.strftime("%d-%m-%Y %H:%M")
            self.send_message(receiver, message)
            self.send(json.dumps({
                'type': 'send_message', 
                'to': f'{receiver}',
                'body': message,
                'time': current_time
            }));

        elif text_data_json['type'] == 'logout_request':
            print(text_data_json)
            close_code = 1000
            self.disconnect(close_code)

    def send_roster(self):
        if hasattr(self, 'xmpp_client'):
            contacts = self.xmpp_client.get_contacts()
            self.send(text_data=json.dumps({
                'type': 'roster_update',
                'contacts': contacts
            }))
        else:
            self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'XMPP client not initialized'
            }))

    def get_presence(self, contact_jid):
        if hasattr(self, 'xmpp_client'):
            presence = self.xmpp_client.get_presence(contact_jid)
            print('Type of presence is:', type(presence))
            print(f'{contact_jid}: {presence}')

    def send_message(self, receiver, message):
        if hasattr(self, 'xmpp_client'):
            self.xmpp_client.send_message(receiver, message)

    def message_handler(self, conn, msg):
        xml_to_dict = xmltodict.parse(str(msg))
        if 'body' not in xml_to_dict['message']:
            xml_to_dict['message']['body'] = None
        print('XML Message:', xml_to_dict)
        utc_now = datetime.datetime.utcnow()
        local_time_difference = datetime.timedelta(hours=-5)
        local_time_now = utc_now + local_time_difference
        current_time = local_time_now.strftime("%d-%m-%Y %H:%M")
        new_dict = {
            'type': 'receive_message',
            'from': xml_to_dict['message']['@from'],
            'body': xml_to_dict['message']['body'],
            'time': current_time
        }

        json_message = json.dumps(new_dict)
        print('JSON Message:', json_message)
        self.send(text_data=json_message)

    def disconnect(self, close_code):
        if hasattr(self, 'xmpp_client'):
            #self.xmpp_client.logout()
            self.send(text_data=json.dumps({
                'type': 'xmpp_logout',
                'message': 'You logged out of the XMPP server',
            }))
        self.close()

class SignUpConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        if 'type' in text_data_json and text_data_json['type'] == 'signup_request':

            user = text_data_json['address'].split('@')[0]
            password = text_data_json['password']
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            url = "https://bryanyep.com:5443/api/register"
            data = {
                "user": user,
                "host": "bryanyep.com",
                "password": password
            }

            admin_user = "admin@bryanyep.com"
            admin_password = tests.key
            response = requests.post(url, json=data, auth=HTTPBasicAuth(admin_user, admin_password), verify=False)

            print(f'Response: {response.status_code}')

            if response.status_code == 200:
                self.send(text_data=json.dumps({
                    'type': 'signup_success',
                    'success': True,
                    'message': 'You created a new XMPP account at bryanyep.com!',
                    'new_user': f'{user}@bryanyep.com'
                }))

 
    def disconnect(self, close_code):
        pass

