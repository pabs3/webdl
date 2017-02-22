#!/usr/bin/env python3

from common import load_root_node
import fnmatch
import logging
import os
import shutil
import sys

HISTORY_FILENAME = ".history.txt"
PATTERN_FILENAME = ".patterns.txt"

class DownloadList(object):
    def __init__(self):
        self.seen_list = set()
        self._load_history_file()
        self.f = open(HISTORY_FILENAME, "a")

    def _load_history_file(self):
        self._move_old_file("downloaded_auto.txt")
        self._move_old_file(".downloaded_auto.txt")

        try:
            with open(HISTORY_FILENAME, "r") as f:
                for line in f:
                    self.seen_list.add(line.strip())
        except Exception as e:
            logging.error("Could not open history file: %s -- %s", HISTORY_FILENAME, e)

    def _move_old_file(self, old_filename):
        if os.path.isfile(old_filename) and not os.path.isfile(HISTORY_FILENAME):
            logging.info("Migrating download history from %s to %s", old_filename, HISTORY_FILENAME)
            shutil.move(old_filename, HISTORY_FILENAME)

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


def process_one_dir(destdir, patternfile):
    os.chdir(destdir)
    node = load_root_node()
    download_list = DownloadList()

    for line in open(patternfile):
        search = line.strip().split("/")
        match(download_list, node, search)

def check_directories(download_dirs):
    result = []
    failed = False

    for d in download_dirs:
        d = os.path.abspath(d)
        if not os.path.isdir(d):
            print("Not a directory!", d)
            failed = True

        pattern_filename = os.path.join(d, PATTERN_FILENAME)
        if not os.path.isfile(pattern_filename):
            print("Missing file!", pattern_filename)
            failed = True

        result.append((d, pattern_filename))

    if failed:
        print("Exiting!")
        sys.exit(1)

    return result

def process_dirs(download_dirs):
    for download_dir, pattern_filename in check_directories(download_dirs):
        logging.info("Processing directory: %s", download_dir)
        process_one_dir(download_dir, pattern_filename)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: %s download_dir [download_dir ...]" % sys.argv[0])
        sys.exit(1)

    if len(sys.argv) == 3 and os.path.isfile(sys.argv[2]):
        # Backwards compatibility with old argument format
        destdir = os.path.abspath(sys.argv[1])
        patternfile = os.path.abspath(sys.argv[2])
        run = lambda: process_one_dir(destdir, patternfile)

    else:
        run = lambda: process_dirs(sys.argv[1:])

    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")
