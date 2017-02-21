#!/usr/bin/env python3

from common import load_root_node
import fnmatch
import logging
import os
import sys

DOWNLOAD_HISTORY_FILES = [
    ".downloaded_auto.txt",
    "downloaded_auto.txt",
]

class DownloadList(object):
    def __init__(self):
        self.seen_list = set()
        for filename in DOWNLOAD_HISTORY_FILES:
            if os.path.isfile(filename):
                break
        else:
            filename = DOWNLOAD_HISTORY_FILES[0]
        try:
            self.f = open(filename, "r")
            for line in self.f:
                self.seen_list.add(line.strip())
            self.f.close()
        except Exception as e:
            logging.error("Could not open: %s -- %s", filename, e)
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
            if node.download():
                download_list.mark_seen(node)
            else:
                logging.error("Failed to download! %s", node.title)
        return

    if count >= len(pattern):
        logging.error("No match found for pattern:", "/".join(pattern))
        return
    p = pattern[count]
    for child in node.get_children():
        if fnmatch.fnmatch(child.title, p):
            match(download_list, child, pattern, count+1)


def main(destdir, patternfile):
    os.chdir(destdir)
    node = load_root_node()
    download_list = DownloadList()

    for line in open(patternfile):
        search = line.strip().split("/")
        match(download_list, node, search)

if __name__ == "__main__":
    try:
        destdir = os.path.abspath(sys.argv[1])
        patternfile = os.path.abspath(sys.argv[2])
    except IndexError:
        print("Usage: %s destdir patternfile" % sys.argv[0])
        sys.exit(1)
    try:
        main(destdir, patternfile)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")

