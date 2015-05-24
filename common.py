from lxml import etree, html
import cookielib
import json
try:
    import hashlib
except ImportError:
    import md5 as hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib
import urllib2
import urlparse


try:
    import autosocks
    autosocks.try_autosocks()
except ImportError:
    pass

CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "webdl")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:21.0) Gecko/20100101 Firefox/21.0"

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

###    import plus7
###    plus7.fill_nodes(root_node)

    import brightcove
    brightcove.fill_nodes(root_node)

    return root_node

valid_chars = frozenset("-_.()!@#%^ abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
def sanify_filename(filename):
    filename = filename.encode("ascii", "ignore")
    filename = "".join(c for c in filename if c in valid_chars)
    return filename

cookiejar = cookielib.CookieJar()
urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
def _urlopen(url, referrer=None):
    req = urllib2.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    if referrer:
        req.add_header("Referer", referrer)
    return urlopener.open(req)

def urlopen(url, max_age):
### print url
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    if max_age <= 0:
        return _urlopen(url)

    filename = hashlib.md5(url).hexdigest()
    filename = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filename):
        file_age = int(time.time()) - os.path.getmtime(filename)
        if file_age < max_age:
            return open(filename)

    src = _urlopen(url)
    dst = open(filename, "wb")
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

def grab_text(url, max_age):
    f = urlopen(url, max_age)
    text = f.read().decode("utf-8")
    f.close()
    return text

def grab_html(url, max_age):
    f = urlopen(url, max_age)
    doc = html.parse(f, html.HTMLParser(encoding="utf-8", recover=True))
    f.close()
    return doc

def grab_xml(url, max_age):
    f = urlopen(url, max_age)
    doc = etree.parse(f, etree.XMLParser(encoding="utf-8", recover=True))
    f.close()
    return doc

def grab_json(url, max_age, skip_assignment=False, skip_function=False):
    f = urlopen(url, max_age)
    if skip_assignment:
        text = f.read()
        pos = text.find("=")
        doc = json.loads(text[pos+1:])
    elif skip_function:
        text = f.read()
        pos = text.find("(")
        rpos = text.rfind(")")
        doc = json.loads(text[pos+1:rpos])
    else:
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


def check_command_exists(cmd):
    try:
        subprocess.check_output(cmd)
        return True
    except Exception:
        return False

def generate_remux_cmd(infile, outfile):
    if check_command_exists(["avconv", "--help"]):
        return [
            "avconv",
            "-i", infile,
            "-bsf:a", "aac_adtstoasc",
            "-acodec", "copy",
            "-vcodec", "copy",
            outfile,
        ]

    if check_command_exists(["ffmpeg", "--help"]):
        return [
            "ffmpeg",
            "-i", infile,
            "-bsf:a", "aac_adtstoasc",
            "-acodec", "copy",
            "-vcodec", "copy",
            outfile,
        ]

    raise Exception("You must install ffmpeg or libav-tools")

def remux(infile, outfile):
    print "Converting %s to mp4" % infile
    cmd = generate_remux_cmd(infile, outfile)
    if not exec_subprocess(cmd):
        # failed, error has already been logged
        return False
    try:
        flv_size = os.stat(infile).st_size
        mp4_size = os.stat(outfile).st_size
        if abs(flv_size - mp4_size) < 0.1 * flv_size:
            os.unlink(infile)
            return True
        else:
            print >>sys.stderr, "The size of", outfile, "is suspicious, did avconv fail?"
            return False
    except Exception, e:
        print >>sys.stderr, "Conversion failed", e
        return False

def convert_to_mp4(filename):
    with open(filename) as f:
        fourcc = f.read(4)
    basename, ext = os.path.splitext(filename)

    if ext == ".mp4" and fourcc == "FLV\x01":
        os.rename(filename, basename + ".flv")
        ext = ".flv"
        filename = basename + ext

    if ext in (".flv", ".ts"):
        filename_mp4 = basename + ".mp4"
        return remux(filename, filename_mp4)

    return ext == ".mp4"


def download_hds(filename, video_url, pvswf=None):
    filename = sanify_filename(filename)
    print "Downloading: %s" % filename

    video_url = video_url.replace("http://", "hds://")
    if pvswf:
        param = "%s pvswf=%s" % (video_url, pvswf)
    else:
        param = video_url

    cmd = [
        "livestreamer",
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
    video_url = video_url.replace("http://", "hlsvariant://")
    print "Downloading: %s" % filename
    cmd = [
        "livestreamer",
        "-o", filename,
        video_url,
        "best",
    ]
    if exec_subprocess(cmd):
        return convert_to_mp4(filename)
    else:
        return False

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
                newk.append(int(c))
            else:
                for subc in c.split():
                    if subc not in ignore_list:
                        newk.append(subc)
        return newk

    return sorted(l, key=key_func)

def append_to_qs(url, params):
    r = list(urlparse.urlsplit(url))
    qs = urlparse.parse_qs(r[3])
    for k, v in params.iteritems():
        if v is not None:
            qs[k] = v
        elif qs.has_key(k):
            del qs[k]
    r[3] = urllib.urlencode(qs, True)
    url = urlparse.urlunsplit(r)
    return url

