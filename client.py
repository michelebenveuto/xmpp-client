
import asyncio
from asyncio.tasks import sleep
import logging
from getpass import getpass
from aioconsole import ainput, aprint

import slixmpp
from slixmpp import jid
from slixmpp.exceptions import IqError, IqTimeout
from argparse import ArgumentParser

class UserClient(slixmpp.ClientXMPP):
    
    def __init__(self, jid, password):
        super().__init__(jid, password)

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("change_status", self.wait_for_presences)
        self.add_event_handler("message", self.message)
        self.talking_to = None
        self.received = set()
        self.presences_received = asyncio.Event()

    async def start(self,event):
        try:
            await self.get_roster()
        except IqError as err:
            print('Error: %s' %err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')
        self.send_presence()
        
        print('Geting your Roster...\n')
        await asyncio.sleep(10)

        await self.show_roster()
        
        await self.client_loop()
        self.disconnect()
    
    async def show_roster(self):
        groups = self.client_roster.groups()
        for group in groups:
            print('\n%s' % group)
            print('-' * 72)
            for jid in groups[group]:
                sub = self.client_roster[jid]['subscription']
                name = self.client_roster[jid]['name']
                if self.client_roster[jid]['name']:
                    print(' %s (%s) [%s]' % (name, jid, sub))
                else:
                    print(' %s [%s]' % (jid, sub))

    def start_conv(self, jid):
        if "@" not in jid:
            jid += "@alumchat.xyz"
        if jid in self.client_roster.keys() or jid =='echobot@alumchat.xyz':
                self.talking_to = jid
                return True
        else:
            return False

    async def message(self,msg):
        if msg['type'] in ('chat', 'normal'):
            await aprint(msg['from'], ':',msg['body'])

    def wait_for_presences(self, pres):
        self.received.add(pres['from'].bare)
        if len(self.received) >= len(self.client_roster.keys()):
            self.presences_received.set()
        else:
            self.presences_received.clear()
    
    async def handle_conv(self):
        print("Chating with ", self.talking_to)
        print("\n"*3)
        continueConv = True
        while continueConv:
            user_input = await ainput('-> ')
            if user_input != "/quit":
                self.send_message(mto = self.talking_to, mbody=user_input, mtype="chat")
                await sleep(0.5)
            else:
                self.talking_to = None
                continueConv = False
    
    def show_menu(self):
        menu = """
        1)Individual Chats
        2)Gruop Chats
        3)Show Roster
        4)Add a Friend
        5)Exit
        """
        return menu

    async def client_loop(self):
        wants_to_continue = True
        while wants_to_continue:
            print(self.show_menu())
            menu_choice = await ainput("-> ")
            menu_choice = int(menu_choice)
            if menu_choice == 1:
                print("Your contacts")
                await self.show_roster()
                talk_to = await ainput("-> ")
                known = self.start_conv(talk_to)
                if known:
                    await self.handle_conv()
                else:
                    print(talk_to, "is not in your contacts")
            elif menu_choice == 2:
                pass
            elif menu_choice == 3:
                print('Your contacts %s' % self.boundjid.bare)
                await self.show_roster()
            elif menu_choice == 4:
                to = await ainput("Friend to Add:")
                await self.send_friend_request(to)
            else:
                wants_to_continue = False
                
        self.disconnect()

    async def send_friend_request(self, to):
        if "@" not in to:
            to += "@alumchat.xyz"
        print("Sending friend request to: ",to)
        try:
            self.send_presence_subscription(to,self.boundjid.bare)
            await sleep(0.5)
            print("Friend Request succesfully sent to: ", to)
        except:
            print("Couldn't add friend, are you sure ", to, " is on the server?")

if __name__ =='__main__':
    parser = ArgumentParser(description=UserClient.__doc__)

    parser.add_argument("-j", dest="jid")
    parser.add_argument("-p", dest="password")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = input("Username: ")
    if args.password is None:
        args.password = getpass("Password: ")
    
    xmpp = UserClient(args.jid, args.password)
    xmpp.register_plugin('xep_0199')

    xmpp.connect(address=('alumchat.xyz',5223))
    xmpp.process(forever=False)