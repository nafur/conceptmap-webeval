#!/usr/bin/python3

host = "localhost"
port = 5000

import threading
import time
import webbrowser

def openPage():
	time.sleep(1)
	webbrowser.open("http://%s:%d" % (host,port))
t = threading.Thread(target = openPage)
#t.start()

from webeval import app
app.run(host = host, port = port, debug=True)
