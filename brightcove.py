import logging
import re
import sys

from common import grab_json, download_hls, download_hds, Node, append_to_qs

CH9_TOKEN = "ogxhPgSphIVa2hhxbi9oqtYwtg032io4B4-ImwddYliFWHqS0UfMEw.."
CH10_TOKEN = "90QPG7lQuLJAc4s82qA-T_UoDhz_VBFK6SGstWDB0jZH8eu1SZQDFA.."

BRIGHTCOVE_API = "http://api.brightcove.com/services/library?"


class BrightcoveVideoNode(Node):
    def __init__(self, title, parent, token, video_id):
        Node.__init__(self, title, parent)
        self.can_download = True
        self.token = token
        self.video_id = video_id

    def download(self):
        f = None
        try_streams = [self.try_hds, self.try_hls]

        while f is None and try_streams:
            f = try_streams.pop()()

        if f is None:
            logging.error("No HLS or HDS stream available for: %s", self.title)
            return False

        return f()

    def try_hls(self):
        desc_url = append_to_qs(BRIGHTCOVE_API, {
            "token": self.token,
            "command": "find_video_by_id",
            "video_fields": "HLSURL",
            "video_id": self.video_id,
        })

        doc = grab_json(desc_url)
        video_url = doc and doc["HLSURL"]
        if not video_url:
            return

        filename = self.title + ".ts"
        return lambda: download_hls(filename, video_url)

    def try_hds(self):
        desc_url = append_to_qs(BRIGHTCOVE_API, {
            "token": self.token,
            "command": "find_video_by_id",
            "video_fields": "hdsManifestUrl",
            "video_id": self.video_id,
        })

        doc = grab_json(desc_url)
        video_url = doc and doc["hdsManifestUrl"]
        if not video_url:
            return

        filename = self.title + ".flv"
        return lambda: download_hds(filename, video_url)


class BrightcoveRootNode(Node):
    def __init__(self, title, parent, token):
        Node.__init__(self, title, parent)
        self.token = token
        self.series_nodes = {}

    def get_series_node(self, series_name):
        series_name = series_name.split("-")[0].strip()
        key = series_name.lower()
        node = self.series_nodes.get(key, None)
        if node is None:
            node = Node(series_name, self)
            self.series_nodes[key] = node
        return node

    def fill_children(self):
        page_number = 0
        while page_number < 100:
            url = self.get_all_videos_url(page_number)
            page_number += 1

            page = grab_json(url)
            items = page["items"]
            if len(items) == 0:
                break

            for video_desc in items:
                self.process_video(video_desc)

    def process_video(self, video_desc):
        if not video_desc["customFields"]:
            return

        video_id = video_desc["id"]
        title = self.get_video_title(video_desc)
        series_name = self.get_series_name(video_desc)

        parent_node = self.get_series_node(series_name)
        BrightcoveVideoNode(title, parent_node, self.token, video_id)

    def get_video_title(self, video_desc):
        raise NotImplementedError()

    def get_series_name(self, video_desc):
        raise NotImplementedError()

    def get_all_videos_url(self, page_number):
        raise NotImplementedError()


class Ch9RootNode(BrightcoveRootNode):
    def __init__(self, root_node):
        BrightcoveRootNode.__init__(self, "Nine", root_node, CH9_TOKEN)

    def get_video_title(self, video_desc):
        title = video_desc["name"]
        season = video_desc["customFields"].get("season", "")
        episode = video_desc["customFields"].get("episode", "1").rjust(2, "0")
        series = self.get_series_name(video_desc)

        if re.match(R"ep(isode)?\s*[0-9]+\s*:", title.lower()):
            title = title.split(":", 1)[1].strip()

        title = "%s - %sx%s - %s" % (
            series,
            season,
            episode,
            title
        )
        return title

    def get_series_name(self, video_desc):
        series = video_desc["customFields"].get("series", None)
        if not series:
            series = video_desc["name"]
        return series

    def get_all_videos_url(self, page_number):
        return append_to_qs(BRIGHTCOVE_API, {
            "token": self.token,
            "command": "search_videos",
            "video_fields": "id,name,customFields",
            "custom_fields": "series,season,episode",
            "sort_by": "PUBLISH_DATE",
            "page_number": str(page_number),
        })


class Ch10RootNode(BrightcoveRootNode):
    def __init__(self, root_node):
        BrightcoveRootNode.__init__(self, "Ten", root_node, CH10_TOKEN)

    def get_video_title(self, video_desc):
        return video_desc["name"]

    def get_series_name(self, video_desc):
        return video_desc["customFields"]["tv_show"]

    def get_all_videos_url(self, page_number):
        return append_to_qs(BRIGHTCOVE_API, {
            "token": self.token,
            "command": "search_videos",
            "video_fields": "id,name,customFields",
            "custom_fields": "tv_show",
            "sort_by": "PUBLISH_DATE",
            "any": "video_type_long_form:Full Episode",
            "page_number": str(page_number),
        })


def fill_nodes(root_node):
    # Ch9RootNode(root_node) -- Need a new API token
    Ch10RootNode(root_node)

