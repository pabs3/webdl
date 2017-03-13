# WebDL #

WebDL is a set of Python scripts to grab video from online Free To Air Australian channels.


## News

### 2017-02-24
* Now requires Python3, use the `python2` branch if you need the old version.
* Recommended installation is now with `virtualenv` and `pip` to install dependencies.
* Removed some custom logic in favour of the `requests` and `requests_cache` libraries.
* `autograbber.py` can write to multiple directories, previous command line args are still supported.


## Installation using pip

Install the following packages using your package manager:

* Python 3.2+ (including dev package)
* ffmpeg or libav-tools

Clone the WebDL repository:
```
git clone https://bitbucket.org/delx/webdl
cd webdl
```

Set up a Python virtualenv and use pip to install the other dependencies:
```
virtualenv --python python3 .virtualenv
. .virtualenv/bin/activate
pip install -r requirements.txt
```

Whenever you want to run WebDL you must source the `.virtualenv/bin/activate` script from your shell.


## Installation on Debian/Ubuntu

Install Python 3 and needed libraries:
```
apt-get install python3 python3-lxml python3-requests python3-requests-cache
```


Install Livestreamer and PyCrypto. Ubuntu packages this as Python 2:
```
apt-get install livestreamer python-crypto
```


Install ffmpeg:
```
apt-get install ffmpeg
```

## Interactive usage (grabber.py)

You can run WebDL interactively to browse categories and episode lists and download TV episodes.

```
$ ./grabber.py
 1) ABC iView
 2) SBS
 0) Back
Choose> 1
 1) ABC 4 Kids
 2) Arts & Culture
 3) Comedy
 4) Documentary
<snipped>
Choose> 4
 1) ABC Open Series 2012
 2) Art Of Germany
 3) Baby Beauty Queens
 4) Catalyst Series 13
<snipped>
Choose> 4
 1) Catalyst Series 13 Episode 15
 2) Catalyst Series 13 Episode 16
 0) Back
Choose> 1
RTMPDump v2.3
(c) 2010 Andrej Stepanchuk, Howard Chu, The Flvstreamer Team; license: GPL
Connecting ...
INFO: Connected...
Starting download at: 0.000 kB
```

The bolded parts are what you type. Note that you can go back on any screen by typing “0”. At the list of episodes you can download a single episode by typing one number, or multiple episodes by typing several numbers separated by spaces.



## Cron scripted usage (autograbber.py)

You can schedule a regular download of your favourite shows.

```
# m    h  dom mon dow   command
  0    1   *   *   *     ./autograbber.py /videos/ABC4Kids /videos/Insight
```

Each of these directories should contain a `.patterns.txt` with shell-style globs:

```
ABC iView/By Channel/ABC4Kids/*/*
SBS/Channel/SBS1/Insight*
```

Whenever an episode is downloaded it is recorded into `.downloaded_auto.txt`. Even if you move the files somewhere else they will not be redownloaded.


## Bug reports

Please raise issues on the [Bitbucket project](https://bitbucket.org/delx/webdl/issues?status=new&status=open).
