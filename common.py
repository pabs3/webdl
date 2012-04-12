# vim:ts=4:sts=4:sw=4:noet

from lxml import etree
import json
try:
	import hashlib
except ImportError:
	import md5 as hashlib
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

	print "Loading iView episode data...",
	sys.stdout.flush()
	import iview
	iview_node = Node("ABC iView", root_node)
	iview.fill_nodes(iview_node)
	print "done"

	print "Loading SBS episode data...",
	sys.stdout.flush()
	import sbs
	sbs_node = Node("SBS", root_node)
	sbs.fill_nodes(sbs_node)
	print "done"

	return root_node

valid_chars = frozenset("-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
def sanify_filename(filename):
    filename = filename.encode("ascii", "ignore")
    filename = "".join(c for c in filename if c in valid_chars)
    return filename


def urlopen(url, max_age):
	if not os.path.isdir(CACHE_DIR):
		os.makedirs(CACHE_DIR)

	if max_age <= 0:
		return urllib.urlopen(url)

	filename = hashlib.md5(url).hexdigest()
	filename = os.path.join(CACHE_DIR, filename)
	if os.path.exists(filename):
		file_age = int(time.time()) - os.path.getmtime(filename)
		if file_age < max_age:
			return open(filename)

	src = urllib.urlopen(url)
	dst = open(filename, "w")
	try:
		shutil.copyfileobj(src, dst)
	except Exception, e:
		try:
			os.unlink(filename)
		except OSError:
			pass
		raise e
	src.close()
	dst.close()

	return open(filename)

def grab_xml(url, max_age):
	f = urlopen(url, max_age)
	doc = etree.parse(f)
	f.close()
	return doc

def grab_json(url, max_age):
	f = urlopen(url, max_age)
	doc = json.load(f)
	f.close()
	return doc

def download_rtmp(filename, vbase, vpath, hash_url=None):
	filename = sanify_filename(filename)
	print "Downloading: %s" % filename
	if vpath.endswith(".flv"):
		vpath = vpath[:-4]
	cmd = [
		"rtmpdump",
		"-o", filename,
		"-r", vbase,
		"-y", vpath,
	]
	print cmd
	if hash_url is not None:
		cmd += ["--swfVfy", hash_url]
	try:
		p = subprocess.Popen(cmd)
		ret = p.wait()
		if ret != 0:
			print >>sys.stderr, "rtmpdump exited with error code:", ret
			return False
		else:
			return True
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
	filename = sanify_filename(filename)
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

