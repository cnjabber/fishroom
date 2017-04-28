#!/usr/bin/env python3
from .photostore import BasePhotoStore
from io import BytesIO
import imghdr
import functools
import hashlib


class BaseFileStore(object):

    def upload_file(self, filename):
        raise Exception("Not Implemented")


class LocalStore(BaseFileStore, BasePhotoStore):

    def __init__(self, path, base_url):
        self.path = path.strip('/') + '/'
        self.base_url = base_url.strip('/') + '/'

    def upload_image(self, filename=None, filedata=None, tag=None):
        if filedata is None:
            with open(filename, 'rb') as f:
                filedata = f.read()

        filehash = hashlib.blake2b(filedata, digest_size=20).hexdigest()

        with BytesIO(filedata) as f:
            ext = imghdr.what(f)

        name = "%s.%s" % (filehash, ext)
        with open(self.path + name, 'wb') as fw:
            fw.write(filedata)
            fw.close()

        return self.base_url + name

    def upload_file(self, filedata, filename=None, filetype=None):
        if filedata is None:
            with open(filename, 'rb') as f:
                filedata = f.read()

        filehash = hashlib.blake2b(filedata, digest_size=20).hexdigest()
        name = filehash

        with open(self.path + name, 'wb') as fw:
            fw.write(filedata)
            fw.close()

        return self.base_url + name


def get_localstore(redis_client, config):
    from .counter import Counter
    if 'localstore' not in config:
        return None

    c = config['localstore']
    return LocalStore(
        c['path'], c['base_url'],
    )


# vim: ts=4 sw=4 sts=4 expandtab
