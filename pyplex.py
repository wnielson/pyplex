import avahi
import dbus
import httplistener
import logging
import os
import Queue
import re
import signal
import socket
import subprocess
import sys
import udplistener
import urllib2
import xml.etree.cElementTree as et

from pprint import pprint
from pyomxplayer import OMXPlayer
from threading import Thread
from urlparse import urlparse


__all__ = ["ZeroconfService"]
class ZeroconfService:
    """A simple class to publish a network service with zeroconf using
    avahi.

    """

    def __init__(self, name, port, stype="_plexclient._tcp",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text

    def publish(self):
        bus = dbus.SystemBus()
        server = dbus.Interface(
                         bus.get_object(
                                 avahi.DBUS_NAME,
                                 avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)

        g = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        g.Commit()
        self.group = g
        print 'Service published'

    def unpublish(self):
        self.group.Reset()

class hello:        
    def GET(self, message):
        return 'Hello, World'

class xbmcCommands:
    def PlayMedia(self, fullpath, tag, unknown1, unknown2, unknown3):
        global omx
        global parsed_path
        global omxCommand
        global media_key
        global duration
        #print '---'
        #print fullpath
        #print tag
        f = urllib2.urlopen(fullpath)
        s = f.read()
        f.close()
        #print s
        tree = et.fromstring(s)
        #get video
        el = tree.find('./Video/Media/Part')
        key = tree.find('./Video')
        key = key.attrib['ratingKey']
        print key
        #print el.attrib['key']
        print 'fullpath', fullpath
        #Construct the path to the media.
        parsed_path = urlparse(fullpath)
        media_key = key
        duration = int(el.attrib['duration'])
        mediapath = parsed_path.scheme + "://" + parsed_path.netloc + el.attrib['key'] 
        #print 'mediapath', mediapath
        if(omx):
            self.stop()
        omx = OMXPlayer(mediapath, args=omxCommand, start_playback=True)

    def Pause(self, message):
        global omx
        if(omx):
            omx.set_speed(1)
            omx.toggle_pause()

    def Play(self, message):
        global omx
        if(omx):
            ret = omx.set_speed(1)
            if(ret == 0):
                omx.toggle_pause()

    def Stop(self, message):
        global omx
        if(omx):
            omx.stop()

    def stopPyplex(self, message):
        self.stop()
        global service
        #pygame.quit()
        exit()

    def SkipNext(self, message = None):
        if(omx):
            omx.increase_speed()

    def SkipPrevious(self, message = None):
        if(omx):
            omx.decrease_speed()

    def StepForward(self, message = None):
        if(omx):
            omx.increase_speed()

    def StepBack(self, message = None):
        if(omx):
            omx.decrease_speed()

    def BigStepForward(self, message = None):
        if(omx):
            omx.jump_fwd_600()

    def BigStepBack(self, message = None):
        if(omx):
            omx.jump_rev_600()
        
class image:
    def __init__(self, picture):
        # pygame.init()
        self.picture = pygame.image.load(picture)
        self.picture = pygame.transform.scale(self.picture,(1280,1024))

    def set(self):
        # pygame.mouse.set_visible(False)
        pygame.display.set_mode(self.picture.get_size())
        main_surface = pygame.display.get_surface()
        main_surface.blit(self.picture, (0, 0))
        pygame.display.update()

def OMXRunning():
    global pid
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    omxRunning = False
    for line in out.splitlines():
        if 'omxplayer' in line:
            pid = int(line.split(None, 1)[0])
            omxRunning = True
    return omxRunning

def getMiliseconds(s):
    hours, minutes, seconds = (["0", "0"] + s.split(":"))[-3:]
    hours = int(hours)
    minutes = int(minutes)
    seconds = float(seconds)
    miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
    return miliseconds


def quit(omx, udp, http):
    if(omx):
        omx.stop()
    if(udp):
        udp.stop()
        udp.join()
    if(http):
        http.stop()
        http.join()

xbmcCmmd = xbmcCommands()
omx = None
http = None
udp = None
pid = -1


if __name__ == "__main__":
    try:
        print "starting, please wait..."
        global service
        global queue
        global parsed_path
        global media_key
        global omxCommand
        global duration
        duration = 0
        args = len(sys.argv)
        if args > 1: 
            if sys.argv[1] == "hdmi":
                omxCommand = '-o hdmi'
                print "Audo output over HDMI"
        else:
            omxCommand = ''
            print "Audio output over 3,5mm jack"
        media_key = None
        parsed_path = None
        queue = Queue.Queue()
        service = ZeroconfService(name="Raspberry Plex", port=3000, text=["machineIdentifier=pi","version=2.0"])
        service.publish()
        udp = udplistener.udplistener(queue)
        udp.start()
        http = httplistener.httplistener(queue)
        http.start()
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        #f = open(os.path.join(__location__, 'image/logo.png'));
        #image = image(f)
        #image.set()
        while True:
            try:
                command, args = queue.get(True, 2)
                print "Got command: %s, args: %s" %(command, args)
                if not hasattr(xbmcCmmd, command):
                    print "Command %s not implemented yet" % command
                else:
                    func = getattr(xbmcCmmd, command)
                    func(*args)
                
                # service.unpublish()
            except Queue.Empty:
                pass
            if(omx):
                # print omx.position
                if omx.finished:
                    if (getMiliseconds(str(omx.position)) > (duration * .95)):
                        setPlayed = parsed_path.scheme + "://" + parsed_path.netloc + "/:/scrobble?key=" + str(media_key) + "&identifier=com.plexapp.plugins.library"
                        try:
                            f = urllib2.urlopen(setPlayed)
                        except urllib2.HTTPError:
                            print "Failed to update plex that item was played: %s" % setPlayPos
                            pass
                    omx.stop()
                    omx = None
                    continue
                pos = getMiliseconds(str(omx.position))
                #TODO: make setPlayPos a function
                setPlayPos =  parsed_path.scheme + "://" + parsed_path.netloc + '/:/progress?key=' + str(media_key) + '&identifier=com.plexapp.plugins.library&time=' + str(pos) + "&state=playing" 
                try:
                    f = urllib2.urlopen(setPlayPos)
                except urllib2.HTTPError:
                    print "Failed to update plex play time, url: %s" % setPlayPos
                    pass
    except KeyboardInterrupt:
        sys.stdout.write("\rExiting...\n")
        sys.stdout.flush()
        quit(omx, udp, http)
    except:
        print "Caught exception"
        quit(omx, udp, http)
        raise

