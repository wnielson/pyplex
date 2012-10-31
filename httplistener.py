import threading
import socket
import urllib2
import tornado.ioloop, tornado.web

class listenerClass(tornado.web.RequestHandler):

    def initialize(self, queue):
        self.queue = queue

    def get(self):
        string = self.get_argument("command")
        print string
        front = string.index("(")
        end = string.rindex(")")
        print "Front: %d, End: %d" %(front, end)
        command = string[:front]
        commandargs = string[front+1:end].split(';')
        # print command
        #print commandargs
        print "Got HTTP command %s, args: %s" % (command, commandargs)
        self.queue.put((command, commandargs))
        self.write("received")

class hello(tornado.web.RequestHandler):
    def get(self):
        print("Got request, gave Hello")
        self.write('Hello, World')

class httplistener(threading.Thread):
    def __init__(self, queue):
        super(httplistener, self).__init__()
        self.queue = queue
        self._stop = threading.Event()
        self.app = tornado.web.Application([(r'/xbmcCmds/xbmcHttp', listenerClass, dict(queue=queue)), (r'/', hello)])
        self.ioloop = tornado.ioloop.IOLoop.instance()
        print "HTTP Init done"

    def run(self):
        self.app.listen(3000)
        print "Started HTTP listener"
        self.ioloop.start()

    def ioloop_stop(self):
        self.ioloop.stop()

    def stop(self):
        self.ioloop.add_callback(self.ioloop_stop)
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
