import hashlib
import io
import json
import logging
import lxml.etree
import lxml.html
import os
import re
import requests
import requests_cache
import shutil
import signal
import subprocess
import time
import urllib.parse


try:
    import autosocks
    autosocks.try_autosocks()
except ImportError:
    pass


logging.basicConfig(
    format = "%(levelname)s %(message)s",
    level = logging.INFO if os.environ.get("DEBUG", None) is None else logging.DEBUG,
)

CACHE_FILE = os.path.join(
    os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")),
    "webdl",
    "requests_cache"
)
if not os.path.isdir(os.path.dirname(CACHE_FILE)):
    os.makedirs(os.path.dirname(CACHE_FILE))

requests_cache.install_cache(CACHE_FILE, backend='sqlite', expire_after=3600)


class Node(object):
    def __init__(self, title, parent=None):
        self.title = title
        if parent:
            parent.children.append(self)
        self.parent = parent
        self.children = []
        self.can_download = False

    def get_children(self):
        if not self.children:
            self.fill_children()
        return self.children

    def fill_children(self):
        pass

    def download(self):
        raise NotImplemented


def load_root_node():
    root_node = Node("Root")

    import iview
    iview.fill_nodes(root_node)

    import sbs
    sbs.fill_nodes(root_node)

    import brightcove
    brightcove.fill_nodes(root_node)

    return root_node

valid_chars = frozenset("-_.()!@#%^ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
def sanify_filename(filename):
    filename = "".join(c for c in filename if c in valid_chars)
    assert len(filename) > 0
    return filename

def ensure_scheme(url):
    parts = urllib.parse.urlparse(url)
    if parts.scheme:
        return url
    parts = list(parts)
    parts[0] = "http"
    return urllib.parse.urlunparse(parts)

http_session = requests.Session()
http_session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:21.0) Gecko/20100101 Firefox/21.0"

def grab_text(url):
    logging.debug("grab_text(%r)", url)
    request = http_session.prepare_request(requests.Request("GET", url))
    response = http_session.send(request)
    return response.text

def grab_html(url):
    logging.debug("grab_html(%r)", url)
    request = http_session.prepare_request(requests.Request("GET", url))
    response = http_session.send(request, stream=True)
    doc = lxml.html.parse(io.StringIO(response.text), lxml.html.HTMLParser(encoding="utf-8", recover=True))
    response.close()
    return doc

def grab_xml(url):
    logging.debug("grab_xml(%r)", url)
    request = http_session.prepare_request(requests.Request("GET", url))
    response = http_session.send(request, stream=True)
    doc = lxml.etree.parse(io.StringIO(response.text), lxml.etree.XMLParser(encoding="utf-8", recover=True))
    response.close()
    return doc

def grab_json(url):
    logging.debug("grab_json(%r)", url)
    request = http_session.prepare_request(requests.Request("GET", url))
    response = http_session.send(request)
    return response.json()

def exec_subprocess(cmd):
    logging.debug("Executing: %s", cmd)
    try:
        p = subprocess.Popen(cmd)
        ret = p.wait()
        if ret != 0:
            logging.error("%s exited with error code: %s", cmd[0], ret)
            return False
        else:
            return True
    except OSError as e:
        logging.error("Failed to run: %s -- %s", cmd[0], e)
    except KeyboardInterrupt:
        logging.info("Cancelled: %s", cmd)
        try:
            p.terminate()
            p.wait()
        except KeyboardInterrupt:
            p.send_signal(signal.SIGKILL)
            p.wait()
    return False


def check_command_exists(cmd):
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False

def find_ffmpeg():
    for ffmpeg in ["avconv", "ffmpeg"]:
        if check_command_exists([ffmpeg, "--help"]):
            return ffmpeg

    raise Exception("You must install ffmpeg or libav-tools")

def find_ffprobe():
    for ffprobe in ["avprobe", "ffprobe"]:
        if check_command_exists([ffprobe, "--help"]):
            return ffprobe

    raise Exception("You must install ffmpeg or libav-tools")

def get_duration(filename):
    ffprobe = find_ffprobe()

    cmd = [
        ffprobe,
        filename,
        "-show_format_entry", "duration",
        "-v", "quiet",
    ]
    output = subprocess.check_output(cmd).decode("utf-8")
    for line in output.split("\n"):
        if line.startswith("duration="):
            return float(line.split("=")[1]) # ffprobe
        if re.match(R'^[0-9.]*$', line):
            return float(line) # avprobe

    raise Exception("Unable to determine video duration of " + filename)

def check_video_durations(flv_filename, mp4_filename):
    flv_duration = get_duration(flv_filename)
    mp4_duration = get_duration(mp4_filename)

    if abs(flv_duration - mp4_duration) > 1:
        logging.error(
            "The duration of %s is suspicious, did the remux fail? Expected %s == %s",
            mp4_filename, flv_duration, mp4_duration
        )
        return False

    return True

def remux(infile, outfile):
    logging.info("Converting %s to mp4", infile)

    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg,
        "-i", infile,
        "-bsf:a", "aac_adtstoasc",
        "-acodec", "copy",
        "-vcodec", "copy",
        "-y",
        outfile,
    ]
    if not exec_subprocess(cmd):
        return False

    if not check_video_durations(infile, outfile):
        return False

    os.unlink(infile)
    return True

def convert_to_mp4(filename):
    with open(filename, "rb") as f:
        fourcc = f.read(4)
    basename, ext = os.path.splitext(filename)

    if ext == ".mp4" and fourcc == b"FLV\x01":
        os.rename(filename, basename + ".flv")
        ext = ".flv"
        filename = basename + ext

    if ext in (".flv", ".ts"):
        filename_mp4 = basename + ".mp4"
        return remux(filename, filename_mp4)

    return ext == ".mp4"


def download_hds(filename, video_url, pvswf=None):
    filename = sanify_filename(filename)
    logging.info("Downloading: %s", filename)

    video_url = "hds://" + video_url
    if pvswf:
        param = "%s pvswf=%s" % (video_url, pvswf)
    else:
        param = video_url

    cmd = [
        "livestreamer",
        "-f",
        "-o", filename,
        param,
        "best",
    ]
    if exec_subprocess(cmd):
        return convert_to_mp4(filename)
    else:
        return False

def download_hls(filename, video_url):
    filename = sanify_filename(filename)
    video_url = "hlsvariant://" + video_url
    logging.info("Downloading: %s", filename)

    cmd = [
        "livestreamer",
        "-f",
        "-o", filename,
        video_url,
        "best",
    ]
    if exec_subprocess(cmd):
        return convert_to_mp4(filename)
    else:
        return False

def download_http(filename, video_url):
    filename = sanify_filename(filename)
    logging.info("Downloading: %s", filename)

    cmd = [
        "curl",
        "--fail", "--retry", "3",
        "-o", filename,
        video_url,
    ]
    if exec_subprocess(cmd):
        return convert_to_mp4(filename)
    else:
        return False

def natural_sort(l, key=None):
    ignore_list = ["a", "the"]
    def key_func(k):
        if key is not None:
            k = key(k)
        k = k.lower()
        newk = []
        for c in re.split("([0-9]+)", k):
            c = c.strip()
            if c.isdigit():
                newk.append(c.zfill(5))
            else:
                for subc in c.split():
                    if subc not in ignore_list:
                        newk.append(subc)
        return newk

    return sorted(l, key=key_func)

def append_to_qs(url, params):
    r = list(urllib.parse.urlsplit(url))
    qs = urllib.parse.parse_qs(r[3])
    for k, v in params.items():
        if v is not None:
            qs[k] = v
        elif k in qs:
            del qs[k]
    r[3] = urllib.parse.urlencode(sorted(qs.items()), True)
    url = urllib.parse.urlunsplit(r)
    return url

