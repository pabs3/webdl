#!/usr/bin/env python
# vim:ts=4:sts=4:sw=4:noet

from common import load_root_node
import fnmatch
import sys

class DownloadList(object):
	def __init__(self, filename):
		self.f = open(filename, "a+")
		self.seen_list = set()
		for line in self.f:
			self.seen_list.add(line.strip())
	
	def has_seen(self, node):
		return node.title in self.seen_list
	
	def mark_seen(self, node):
		self.seen_list.add(node.title)
		self.f.write(node.title + "\n")


def match(download_list, node, pattern):
	if node.can_download:
		if not download_list.has_seen(node):
			if node.download():
				download_list.mark_seen(node)
			else:
				print >>sys.stderr, "Failed to download!", node.title
		return

	p = pattern[0]
	for child in node.children:
		if fnmatch.fnmatch(child.title, p):
			match(download_list, child, pattern[1:])


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

