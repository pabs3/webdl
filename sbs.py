import requests_cache
from common import grab_html, grab_json, grab_xml, download_hls, download_mpd, Node, append_to_qs

import json
import logging
import os
import sys

BASE = "https://www.sbs.com.au"
FULL_VIDEO_LIST = BASE + "/api/video_feed/f/Bgtm9B/sbs-section-programs/"
VIDEO_URL = BASE + "/ondemand/video/single/%s"

NS = {
    "smil": "http://www.w3.org/2005/SMIL21/Language",
}


class SbsVideoNode(Node):
    def __init__(self, title, parent, url):
        Node.__init__(self, title, parent)
        self.video_id = url.split("/")[-1]
        self.can_download = True

    def download(self):
        with requests_cache.disabled():
            doc = grab_html(VIDEO_URL % self.video_id)
        player_params = self.get_player_params(doc)

        error = player_params.get("error", None)
        if error:
            print("Cannot download:", error)
            return False

        release_url = player_params["releaseUrls"]["html"]
        filename = self.title + ".ts"

        hls_url = self.get_hls_url(release_url)
        if hls_url:
            return download_hls(filename, hls_url)
        else:
            return download_mpd(filename, release_url)

    def get_player_params(self, doc):
        for script in doc.xpath("//script"):
            if not script.text:
                continue
            for line in script.text.split("\n"):
                s = "var playerParams = {"
                if s in line:
                    p1 = line.find(s) + len(s) - 1
                    p2 = line.find("};", p1) + 1
                    if p1 >= 0 and p2 > 0:
                        return json.loads(line[p1:p2])
        raise Exception("Unable to find player params for %s: %s" % (self.video_id, self.title))

    def get_hls_url(self, release_url):
        with requests_cache.disabled():
            doc = grab_xml("https:" + release_url.replace("http:", "").replace("https:", ""))
            video = doc.xpath("//smil:video", namespaces=NS)
            if not video:
                return
            video_url = video[0].attrib["src"]
            return video_url

class SbsNavNode(Node):
    def create_video_node(self, entry_data):
        SbsVideoNode(entry_data["title"], self, entry_data["id"])

    def find_existing_child(self, path):
        for child in self.children:
            if child.title == path:
                return child

class SbsRootNode(SbsNavNode):
    def __init__(self, parent):
        Node.__init__(self, "SBS", parent)

    def fill_children(self):
        all_video_entries = self.load_all_video_entries()
        category_and_entry_data = self.explode_videos_to_unique_categories(all_video_entries)
        for category_path, entry_data in category_and_entry_data:
            nav_node = self.create_nav_node(self, category_path)
            nav_node.create_video_node(entry_data)

    def load_all_video_entries(self):
        channels = [
            "Channel/SBS1",
            "Channel/SBS Food",
            "Channel/SBS VICELAND",
            "Channel/SBS World Movies",
            "Channel/Web Exclusive",
        ]

        all_entries = {}
        for channel in channels:
            self.load_all_video_entries_for_channel(all_entries, channel)

        all_entries = list(all_entries.values())
        print(" SBS fetched", len(all_entries))
        return all_entries

    def load_all_video_entries_for_channel(self, all_entries, channel):
        offset = 1
        page_size = 500
        duplicate_warning = False

        while True:
            entries = self.fetch_entries_page(channel, offset, page_size)
            if len(entries) == 0:
                break

            for entry in entries:
                guid = entry["guid"]
                if guid in entries and not duplicate_warning:
                    # https://bitbucket.org/delx/webdl/issues/102/recent-sbs-series-missing
                    logging.warn("SBS returned a duplicate response, data is probably missing. Try decreasing page_size.")
                    duplicate_warning = True

                all_entries[guid] = entry

            offset += page_size
            if os.isatty(sys.stdout.fileno()):
                sys.stdout.write(".")
                sys.stdout.flush()

    def fetch_entries_page(self, channel, offset, page_size):
        url = append_to_qs(FULL_VIDEO_LIST, {
            "range": "%s-%s" % (offset, offset+page_size-1),
            "byCategories": channel,
        })
        data = grab_json(url)
        if "entries" not in data:
            raise Exception("Missing data in SBS response", data)
        return data["entries"]

    def explode_videos_to_unique_categories(self, all_video_entries):
        for entry_data in all_video_entries:
            for category_data in entry_data["media$categories"]:
                category_path = self.calculate_category_path(
                    category_data["media$scheme"],
                    category_data["media$name"],
                )
                if category_path:
                    yield category_path, entry_data

    def calculate_category_path(self, scheme, name):
        if not scheme:
            return
        if scheme == name:
            return
        name = name.split("/")
        if name[0] != scheme:
            name.insert(0, scheme)
        return name

    def create_nav_node(self, parent, category_path):
        if not category_path:
            return parent

        current_path = category_path[0]
        current_node = parent.find_existing_child(current_path)
        if not current_node:
            current_node = SbsNavNode(current_path, parent)
        return self.create_nav_node(current_node, category_path[1:])

def fill_nodes(root_node):
    SbsRootNode(root_node)
