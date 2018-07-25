import argparse
import os
import logging
from slackclient import SlackClient

class Slack(object):
    def __init__(self,token = os.environ.get('SLACK_TOKEN')):
        self.token = token
        if self.token==None:
            logging.error('No slack token')
            raise Exception

        # set up client
        self.client = SlackClient(token)

        # find channels and organize by 'name'
        channels = self.client.api_call('channels.list', exclude_archived=1)['channels']
        self.channels = {x['name']:x for x in channels}

        # find users and organize by 'name'
        users = self.client.api_call('users.list', exclude_archived=1)['members']
        self.users = {x['name']:x for x in users}

        # find ims and organize by 'id'
        ims = self.client.api_call('im.list', exclude_archived=1)['ims']
        self.ims = {x['id']:x for x in users}
        

    def send_slack_message(self,post_to, message, post_as_username=None): #post_to can be channel or user
        # find channel id
        if post_to in self.channels.keys():
            channel_id = self.channels[post_to]['id']
        elif post_to in self.users.keys(): #im
            channel_id = self.users[post_to]['id']
        else:
            logging.error('%s not a valid channel or user'%post_to)
            raise Exception

        # post message
        if post_as_username ==None:
            response = self.client.api_call('chat.postMessage',channel=channel_id,text=message,as_user=True)
        else:
            response = self.client.api_call('chat.postMessage',channel=channel_id,text=message,as_user=False, username=post_as_username)

        # raise exception if message couldn't be posted
        if not response['ok']:
            logging.error('Slack message could not be posted. Response = %s'%response)
            raise Exception
            
        return(response)
    