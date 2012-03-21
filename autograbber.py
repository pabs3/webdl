#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import load_root_node
import fnmatch
import sys

class DownloadList(object):
	def __init__(self, filename):
		self.f = open(filename, "r")
		self.seen_list = set()
		for line in self.f:
			self.seen_list.add(line.strip())
		self.f.close()
		self.f = open(filename, "a")
	
	def has_seen(self, node):
		return node.title in self.seen_list
	
	def mark_seen(self, node):
		self.seen_list.add(node.title)
		self.f.write(node.title + "\n")
		self.f.flush()


def match(download_list, node, pattern, count=0):
	if node.can_download:
		if not download_list.has_seen(node):
			print "Downloading:", node.title
			if node.download():
				download_list.mark_seen(node)
			else:
				print >>sys.stderr, "Failed to download!", node.title
		return

	if count >= len(pattern):
		print "No match found for pattern:", "/".join(pattern)
		return
	p = pattern[count]
	for child in node.children:
		if fnmatch.fnmatch(child.title, p):
			match(download_list, child, pattern, count+1)


def main():
	node = load_root_node()
	download_list = DownloadList("downloaded_auto.txt")

	for search in sys.argv[1:]:
		search = search.split("/")
		match(download_list, node, search)

if __name__ == "__main__":
	try:
		main()
	except (KeyboardInterrupt, EOFError):
		print "\nExiting..."

