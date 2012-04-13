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

	def get_children(self):
		return self.children

	def download(self):
		raise NotImplemented


def load_root_node():
	root_node = Node("Root")

	import iview
	iview.fill_nodes(root_node)

	import sbs
	sbs.fill_nodes(root_node)

	return root_node

valid_chars = frozenset("-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
def sanify_filename(filename):
    filename = filename.encode("ascii", "ignore")
    filename = "".join(c for c in filename if c in valid_chars)
    return filename


def urlopen(url, max_age):
###	print url
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

def exec_subprocess(cmd):
	try:
		p = subprocess.Popen(cmd)
		ret = p.wait()
		if ret != 0:
			print >>sys.stderr, cmd[0], "exited with error code:", ret
			return False
		else:
			return True
	except OSError, e:
		print >>sys.stderr, "Failed to run", cmd[0], e
	except KeyboardInterrupt:
		print "Cancelled", cmd
		try:
			p.terminate()
			p.wait()
		except KeyboardInterrupt:
			p.send_signal(signal.SIGKILL)
			p.wait()
	return False


def convert_flv_mp4(orig_filename):
	basename = os.path.splitext(orig_filename)[0]
	flv_filename = basename + ".flv"
	mp4_filename = basename + ".mp4"
	os.rename(orig_filename, flv_filename)
	print "Converting %s to mp4" % flv_filename
	cmd = [
		"ffmpeg",
		"-i", flv_filename,
		"-acodec", "copy",
		"-vcodec", "copy",
		mp4_filename,
	]
	if not exec_subprocess(cmd):
		return
	try:
		flv_size = os.stat(flv_filename).st_size
		mp4_size = os.stat(mp4_filename).st_size
		if abs(flv_size - mp4_size) < 0.05 * flv_size:
			os.unlink(flv_filename)
		else:
			print >>sys.stderr, "The size of", mp4_filename, "is suspicious, did ffmpeg fail?"
	except Exception, e:
		print "Conversion failed", e

def convert_filename(filename):
	if filename.lower().endswith(".mp4"):
		f = open(filename)
		fourcc = f.read(4)
		f.close()
		if fourcc == "FLV\x01":
			convert_flv_mp4(filename)

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
	if hash_url is not None:
		cmd += ["--swfVfy", hash_url]
	success = exec_subprocess(cmd)
	convert_filename(filename)
	return success

def download_urllib(filename, url):
	filename = sanify_filename(filename)
	print "Downloading: %s" % filename
	try:
		src = urllib.urlopen(url)
		dst = open(filename, "w")
		while True:
			buf = src.read(1024*1024)
			if not buf:
				break
			dst.write(buf)
			sys.stdout.write(".")
			sys.stdout.flush()
		convert_filename(filename)
		return True
	except KeyboardInterrupt:
		print "\nCancelled", url
	finally:
		try:
			src.close()
		except:
			pass
		try:
			dst.close()
		except:
			pass
	return False

