import calendar
from datetime import datetime

__author__ = 'Qyon'

from py2exe import freeze
import hab2pstrotator

import glob

import os
import zipfile


def find_data_files(source, target, patterns):
    """Locates the specified data-files and returns the matches
    in a data_files compatible format.

    source is the root of the source data tree.
        Use '' or '.' for current directory.
    target is the root of the target data tree.
        Use '' or '.' for the distribution directory.
    patterns is a sequence of glob-patterns for the
        files you want to copy.
    """
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source, pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(target, os.path.relpath(filename, source))
                path = os.path.dirname(targetpath)
                ret.setdefault(path, []).append(filename)
    return sorted(ret.items())


freeze(
    version_info={
        'version': hab2pstrotator.__version__,
        'description': hab2pstrotator.__full_app_name__,
        'product_name': hab2pstrotator.__app_name__,
        'company_name': hab2pstrotator.__author__,
        'comments': hab2pstrotator.__author_email__,

    },
    windows=[
        {
            "script": "hab2pstrotator.py",
            "icon_resources": [(0, "spacenearus.ico")]
        }
    ],
    data_files=find_data_files('', '', [
        '*.ico',
    ]),
    options={
        'packages': ['charset_normalizer']
    }
)


def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file))


full_dir_name = '%s_%s' % (hab2pstrotator.__app_name__, hab2pstrotator.__version__)
zip_file_name = "%s.zip" % (full_dir_name,)

datetime_utcnow = calendar.timegm(datetime.now().timetuple())
if os.path.exists(full_dir_name):
    os.rename(full_dir_name, "%s_%s" % (full_dir_name, datetime_utcnow))
os.rename('dist', full_dir_name)
if os.path.exists(zip_file_name):
    os.rename(zip_file_name, "%s_%s" % (zip_file_name, datetime_utcnow))
zipf = zipfile.ZipFile(zip_file_name, 'w', compression=zipfile.ZIP_DEFLATED)
zipdir(full_dir_name, zipf)
zipf.close()
print("Created dist zip file: %s" % (zip_file_name,))
