# -*- encoding:utf-8 -*-

# ~ https://medium.com/@busybus/zipjson-3ed15f8ea85d
# RA, 2019-01-22
# Compress and decompress a JSON object
# License: CC0 -- "No rights reserved"
# For zlib license, see https://docs.python.org/3/license.html

# changes :
#   - added bzip2 compression
#   - sort keys enabled
#   - remove white spaces

import zlib
import bz2
import json
import base64

ZIPJSON_KEY = 'base64(zip(o))'


def json_compress(j, method=lambda data: zlib.compress(data)):

    return {
        ZIPJSON_KEY: base64.b64encode(
            method(
                json.dumps(j, separators=(',', ':')).encode('utf-8')
            )
        ).decode('ascii')
    }


def json_decompress(j, insist=True, method=lambda data: zlib.decompress(data)):
    try:
        assert (j[ZIPJSON_KEY])
        assert (set(j.keys()) == {ZIPJSON_KEY})
    except Exception:
        if insist:
            raise RuntimeError("JSON not in the expected format {" + str(ZIPJSON_KEY) + ": zipstring}")
        else:
            return j

    try:
        j = method(base64.b64decode(j[ZIPJSON_KEY]))
    except Exception:
        raise RuntimeError("Could not decode/unzip the contents")

    try:
        j = json.loads(j)
    except Exception:
        raise RuntimeError("Could interpret the unzipped contents")

    return j


def bzip(j):
    return json_compress(j, lambda data: bz2.compress(data, compresslevel=9))


def unbzip(j):
    return json_decompress(j, lambda data: bz2.decompress(data))


if __name__ == '__main__':

    import unittest

    class TestJsonZipMethods(unittest.TestCase):
        # Unzipped
        unzipped = {'a': "A", 'b': "B"}

        # Zipped
        zipped = {ZIPJSON_KEY: "eJyrVkpUslJyVNJRSgLSTkq1ACPXA+8="}

        # List of items
        items = [123, "123", unzipped]

        def test_json_zip(self):
            self.assertEqual(self.zipped, json_compress(self.unzipped))

        def test_json_unzip(self):
            self.assertEqual(self.unzipped, json_decompress(self.zipped))

        def test_json_zipunzip(self):
            for item in self.items:
                self.assertEqual(item, json_decompress(json_compress(item)))

        def test_json_zipunzip_chinese(self):
            item = {'hello': u"你好"}
            self.assertEqual(item, json_decompress(json_compress(item)))

        def test_json_unzip_insist_failure(self):
            for item in self.items:
                with self.assertRaises(RuntimeError):
                    json_decompress(item, insist=True)

        def test_json_unzip_noinsist_justified(self):
            for item in self.items:
                self.assertEqual(item, json_decompress(item, insist=False))

        def test_json_unzip_noinsist_unjustified(self):
            self.assertEqual(self.unzipped, json_decompress(self.zipped, insist=False))

    unittest.main()
