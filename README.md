# WebDL #

WebDL is a set of Python scripts to grab video from online Free To Air Australian channels.

## Requirements

* [Livestreamer](http://docs.livestreamer.io/install.html)
* python3-pycrypto -- Livestreamer needs this for some videos
* [rtmpdump](https://rtmpdump.mplayerhq.hu)
* python 2.7 (webdl doesn't work with python3 yet)
* python2-lxml (for python2)
* ffmpeg / libav-tools

## Instructions

### Arch Linux
    pacman -S livestreamer python-crypto python2-lxml rtmpdump ffmpeg

### Ubuntu
    apt-get install livestreamer python3-crypto python-lxml rtmpdump libav-tools

### Mac OS X

Warning, this is untested!

    brew install python3 python rtmpdump ffmpeg
    pip3 install livestreamer pycrypto
    pip install lxml

### Then get WebDL itself
    hg clone https://bitbucket.org/delx/webdl
    cd webdl
    ./grabber.py


## Bug reports

Log an issue on the [Bitbucket project](https://bitbucket.org/delx/webdl/issues?status=new&status=open)
