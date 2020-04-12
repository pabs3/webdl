import logging
from common import grab_json, download_hls, Node, append_to_qs

SERIES_LIST_URL = "https://vod.ten.com.au/config/android-v4"
SERIES_DETAIL_URL = "https://v.tenplay.com.au/api/videos/bcquery"

class TenVideoNode(Node):
    def __init__(self, title, parent, video_url):
        Node.__init__(self, title, parent)
        self.can_download = True
        self.video_url = video_url

    def download(self):
        filename = self.title + ".ts"
        return download_hls(filename, self.video_url)

class TenSeriesNode(Node):
    def __init__(self, title, parent, query, expected_tv_show):
        Node.__init__(self, title, parent)
        self.title = title
        self.query = query
        self.expected_tv_show = expected_tv_show
        self.video_ids = set()

    def fill_children(self):
        page_number = 0
        while page_number < 100:
            url = self.get_page_url(self.query, page_number)
            page_number += 1

            page = grab_json(url)
            items = page["items"]
            if len(items) == 0:
                break

            for video_desc in items:
                self.process_video(video_desc)

    def get_page_url(self, query, page_number):
        return append_to_qs(SERIES_DETAIL_URL, {
            "command": "search_videos",
            "page_size": "30",
            "page_number": str(page_number),
        }) + query

    def process_video(self, video_desc):
        video_id = video_desc["id"]
        video_url = video_desc["HLSURL"]
        tv_show = video_desc["customFields"]["tv_show"]
        title = video_desc["name"]

        if video_id in self.video_ids:
            return
        if tv_show != self.expected_tv_show:
            logging.warn("Skipping unexpected video: %s != %s", tv_show, self.expected_tv_show)
            return
        self.video_ids.add(video_id)

        TenVideoNode(title, self, video_url)

class TenRootNode(Node):
    def fill_children(self):
        doc = grab_json(SERIES_LIST_URL)

        for series in doc["Browse TV"]["Shows"]:
            title = series["title"]
            query = series["query"] + series["episodefilter"]
            expected_tv_show = series["tv_show"]

            TenSeriesNode(title, self, query, expected_tv_show)

def fill_nodes(root_node):
    TenRootNode("Ten", root_node)
