# vim:ts=4:sts=4:sw=4:noet

from lxml import etree
import json
import md5
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib


import autosocks
autosocks.try_autosocks()

CACHE_DIR = os.path.expanduser("~/.cache/webdl")

class Node(object):
	def __init__(self, title, parent=None):
		self.title = title
		if parent:
			parent.children.append(self)
		self.parent = parent
		self.children = []
		self.can_download = False

	def download(self):
		raise NotImplemented


def load_root_node():
	root_node = Node("Root")

	import iview
	iview_node = Node("ABC iView", root_node)
	iview.fill_nodes(iview_node)

	import sbs
	sbs_node = Node("SBS", root_node)
	sbs.fill_nodes(sbs_node)

	return root_node


def urlopen(url):
	try:
		os.mkdir(CACHE_DIR)
	except OSError:
		pass

	filename = md5.new(url).hexdigest()
	filename = os.path.join(CACHE_DIR, filename)
	if os.path.exists(filename):
		if int(time.time()) - os.path.getmtime(filename) < 24*3600:
			return open(filename)

	src = urllib.urlopen(url)
	dst = open(filename, "w")
	shutil.copyfileobj(src, dst)
	src.close()
	dst.close()

	return open(filename)

def grab_xml(url):
	f = urlopen(url)
	doc = etree.parse(f)
	f.close()
	return doc

def grab_json(url):
	f = urlopen(url)
	doc = json.load(f)
	f.close()
	return doc

def download_rtmp(filename, vbase, vpath):
	if vpath.endswith(".flv"):
		vpath = vpath[:-4]
	cmd = [
		"rtmpdump",
		"-o", filename,
		"-r", vbase,
		"-y", vpath,
	]
	try:
		p = subprocess.Popen(cmd)
		ret = p.wait()
		if ret != 0:
			print >>sys.stderr, "rtmpdump exited with error code:", ret
			return False
	except OSError, e:
		print >>sys.stderr, "Failed to run rtmpdump!", e
		return False
	except KeyboardInterrupt:
		print "Cancelled", cmd
		try:
			p.terminate()
			p.wait()
		except KeyboardInterrupt:
			p.send_signal(signal.SIGKILL)
			p.wait()

def download_urllib(filename, url):
	print "Downloading: %s -> %s" % (url, filename)
	try:
		src = urllib.urlopen(url)
		dst = open(filename, "w")
		shutil.copyfileobj(src, dst)
		return True
	except KeyboardInterrupt:
		print "\nCancelled", url
	finally:
		src.close()
		dst.close()
	return False

