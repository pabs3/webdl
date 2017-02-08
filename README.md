# WebDL #

WebDL is a set of Python scripts to grab video from online Free To Air Australian channels.

## Requirements

* [Livestreamer](http://docs.livestreamer.io/install.html)
* python 2.7 or 3.2+
* pycrypto -- Livestreamer needs this for some videos
* python-lxml
* ffmpeg / libav-tools

## Installation

### Arch Linux
    pacman -S livestreamer python-crypto python-lxml ffmpeg

### Ubuntu
    apt-get install livestreamer python-crypto python-lxml libav-tools

### Mac OS X

Warning, this is untested!

    brew install python3 ffmpeg
    pip3 install livestreamer pycrypto lxml

### Then get WebDL itself
    git clone https://bitbucket.org/delx/webdl
    cd webdl
    python3 ./grabber.py


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

I have a shell script which looks something like this, I run it daily from crontab.

```
# m    h  dom mon dow   command
  0    1   *   *   *     ./autograbber.py /path/to/video-dir/ /path/to/patterns.txt
```

The patterns.txt file should contain shell-style globs, something like:

```
ABC iView/*/QI*/*
SBS/Programs/Documentary/*/*
```

The above will download all episodes of QI from ABC as well as every SBS documentary. Whenever an episode is downloaded it is recorded into downloaded_auto.txt. Even if you move the files somewhere else they will not be redownloaded.


## Bug reports

Please raise issues on the [Bitbucket project](https://bitbucket.org/delx/webdl/issues?status=new&status=open).
