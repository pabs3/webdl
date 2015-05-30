# WebDL #

WebDL is a set of Python scripts to grab video from online Free To Air Australian channels.

## Requirements

* [Livestreamer](http://docs.livestreamer.io/install.html)
* python 2.7 or 3.2+
* pycrypto -- Livestreamer needs this for some videos
* python-lxml
* ffmpeg / libav-tools

## Instructions

### Arch Linux
    pacman -S livestreamer python-crypto python-lxml ffmpeg

### Ubuntu
    apt-get install livestreamer python-crypto python-lxml libav-tools

### Mac OS X

Warning, this is untested!

    brew install python3 ffmpeg
    pip3 install livestreamer pycrypto lxml

### Then get WebDL itself
    hg clone https://bitbucket.org/delx/webdl
    cd webdl
    python3 ./grabber.py


## Bug reports

Log an issue on the [Bitbucket project](https://bitbucket.org/delx/webdl/issues?status=new&status=open)
