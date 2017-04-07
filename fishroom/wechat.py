#!/usr/bin/env python3
# Using the ItChat web WeChat API (https://github.com/littlecodersh/itchat)
# to forward WeChat messages

import itchat
from itchat.content import TEXT

from requests.exceptions import MissingSchema
from .bus import MessageBus, MsgDirection
from .base import BaseBotInstance, EmptyBot
from .models import Message, ChannelType, MessageType
from .helpers import get_now_date_time, get_logger
from .config import config
import sys
from .db import get_redis

logger = get_logger("WeChat")

# TODO: Do not use global variables if we have better solutions
wxHandle, wxRooms, wxRoomNicks, myUid = None, {}, {}, ''


@itchat.msg_register(TEXT, isFriendChat=False, isGroupChat=True, isMpChat=False)
def on_message(msg):
    global wxHandle, wxRooms, myUid
    logger.info(msg)
    room = msg["FromUserName"]
    if wxRooms.get(room) is None:
        logger.info("Not in rooms to forward!!!")
        return
    if msg["ActualUserName"] == myUid:
        logger.info("My own message:)")
        return

    date, time = get_now_date_time()
    msg_content = msg["Content"]
    msg = Message(
        ChannelType.Wechat,
        msg["ActualNickName"], wxRooms[room], msg_content,
        mtype=MessageType.Text, date=date, time=time)
    wxHandle.send_to_bus(wxHandle,msg)


def wxdebug():
    # Test if these global variables are set
    global wxHandle, wxRooms, wxRoomNicks, myUid
    logger.info("Debugging...")
    logger.info(wxHandle)
    logger.info(wxRooms)
    logger.info(wxRoomNicks)
    logger.info(myUid)


class WechatHandle(BaseBotInstance):

    ChanTag = ChannelType.Wechat

    def __init__(self, roomNicks):
        global wxRooms, myUid
        itchat.auto_login(hotReload=True, enableCmdQR=2)
        all_rooms = itchat.get_chatrooms(update=True)
        for r in all_rooms:
            if r['NickName'] in roomNicks:
                wxRooms[r['UserName']] = r['NickName']
                wxRoomNicks[r['NickName']] = r['UserName']
                logger.info('Room {} found.'.format(r["NickName"]))
            else:
                logger.info('{}: {}'.format(r['UserName'], r['NickName']))

        friends = itchat.get_friends()
        myUid = friends[0]["UserName"]

    def send_to_bus(self, msg):
        raise NotImplementedError()

    def send_msg(self, target, content, sender=None, first=False, **kwargs):
        logger.info("Sending message")
        roomid = wxRoomNicks[target]
        #itchat.send(msg="[{}] {}".format(sender,content), toUserName=target)
        itchat.send(content, toUserName=roomid)


def Wechat2FishroomThread(wx: WechatHandle, bus: MessageBus):
    if wx is None or isinstance(wx, EmptyBot):
        return

    def send_to_bus(self, msg):
        bus.publish(msg)

    wx.send_to_bus = send_to_bus


def Fishroom2WechatThread(wx: WechatHandle, bus: MessageBus):
    if wx is None or isinstance(wx, EmptyBot):
        logger.info("Error creating Fishroom2WechatThread")
        return
    for msg in bus.message_stream():
        wx.forward_msg_from_fishroom(msg)


def init():
    global wxHandle
    redis_client = get_redis()
    im2fish_bus = MessageBus(redis_client, MsgDirection.im2fish)
    fish2im_bus = MessageBus(redis_client, MsgDirection.fish2im)

    roomNicks = [b["wechat"]
                for _, b in config['bindings'].items() if "wechat" in b]
    wxHandle = WechatHandle(roomNicks)

    return (
        wxHandle,
        im2fish_bus, fish2im_bus,
    )


def main():
    if "wechat" not in config:
        return

    from .runner import run_threads
    bot, im2fish_bus, fish2im_bus = init()
    wxdebug()
    # The two threads and itchat.run are all blocking,
    # so put all of them in run_threads
    run_threads([
        (Wechat2FishroomThread, (bot, im2fish_bus, ), ),
        (Fishroom2WechatThread, (bot, fish2im_bus, ), ),
        (itchat.run, (), )
    ])


def test():
    global wxHandle
    roomNicks = [b["wechat"] for _, b in config['bindings'].items()]
    wxHandle = WechatHandle(roomNicks)

    def send_to_bus(self, msg):
        logger.info(msg.dumps())
    wxHandle.send_to_bus = send_to_bus
    wxHandle.process(block=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default=False, action="store_true")
    args = parser.parse_args()

    if args.test:
        test()
    else:
        main()

# vim: ts=4 sw=4 sts=4 expandtab
