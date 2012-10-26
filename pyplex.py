import web, urllib2, re, xml.etree.cElementTree as et
from pyomxplayer import OMXPlayer
from urlparse import urlparse
import avahi, dbus
from pprint import pprint
import socket, pygame.image, pygame.display, subprocess, signal, os

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


        
urls = (
    '/xbmcCmds/xbmcHttp','xbmcCmdsXbmcHttp',
    '/(.*)', 'stop', 'hello'
)
app = web.application(urls, globals())

class hello:        
    def GET(self,name):
        return 'Hello, World'

class xbmcCmdsXbmcHttp:
    def GET(self):
        string= urllib2.unquote(web.ctx.query)
        pprint(web.ctx.query) 
        #Get command
        commandparse = re.search('command=(.*)\(.*', string)
        command = commandparse.group(1)
        #Get the args
        commandparse = re.search('.*\((.*)\).*',string)
        commandargs = commandparse.group(1).split(';')
        # print command
        #print commandargs
        result = getattr(xbmcCmmd, command)(*commandargs)
        return 'received'

class xbmcCommands:
    def PlayMedia(self, fullpath, tag, unknown1, unknown2, unknown3):
        #print '---'
        #print fullpath
        #print tag
        f = urllib2.urlopen(fullpath)
        s = f.read()
        f.close()
        ## print s
        tree = et.fromstring(s)
        #get video
        el = tree.find('./Video/Media/Part')
        #print el.attrib['key']
        print 'fullpath', fullpath
        #Construct the path to the media.
        o = urlparse(fullpath)
        mediapath = o.scheme + "://" + o.netloc + el.attrib['key'] 
        #print 'mediapath', mediapath
        global omx
        self.stopOMX()
        omx = OMXPlayer(mediapath)
        omx.toggle_pause()

    def stopOMX(self):
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            if 'omxplayer' in line:
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)

class stop():
    def GET(self):
        global omx
        omx.stop()
        return 'received'

class image:
    def __init__(self, picture):
        self.picture = pygame.image.load(picture)
        self.picture = pygame.transform.scale(self.picture,(1280,1024))

    def set(self):
        pygame.display.set_mode(self.picture.get_size())
        main_surface = pygame.display.get_surface()
        main_surface.blit(self.picture, (0, 0))
        pygame.display.update()
xbmcCmmd = xbmcCommands()


if __name__ == "__main__":
    print "starting, please wait..."
    service = ZeroconfService(name="Raspberry Plex", port=3000)
    service.publish()
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    f = open(os.path.join(__location__, 'image/logo.png'));
    image = image(f)
    image.set()
    
    app.run()
    # service.unpublish()

