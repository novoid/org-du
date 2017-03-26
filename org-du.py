#!/usr/bin/env python3
# -*- coding: utf-8 -*-
PROG_VERSION = u"Time-stamp: <2017-03-23 23:48:26 vk>"

## TODO:
## - fix parts marked with «FIXXME»
## -


## ===================================================================== ##
##  You might not want to modify anything below this line if you do not  ##
##  know, what you are doing :-)                                         ##
## ===================================================================== ##

import importlib


def save_import(library):
    try:
        globals()[library] = importlib.import_module(library)
    except ImportError:
        print("Could not find Python module \"" + library + "\".\nPlease install it, e.g., with \"sudo pip install " + library + "\".")
        sys.exit(2)

import re
import sys
import os
save_import('argparse')  # for handling command line arguments
save_import('time')
save_import('logging')
save_import('codecs')    # for handling Unicode content in .tagfiles

PROG_VERSION_DATE = PROG_VERSION[13:23]

DESCRIPTION = "org-du parses a list of Org-mode files and generates\n\
output similar to \"du\" (disk usage) but with lines\n\
of Org-mode instead of kilobytes."

EPILOG = u"Verbose description: http://Karl-Voit.at/ FIXXME\n\
\n\
:copyright: (c) by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v3 or any later version\n\
:URL: https://github.com/novoid/org-du\n\
:bugreports: via github or <tools@Karl-Voit.at>\n\
:version: " + PROG_VERSION_DATE + "\n"


## FIXXME: separate tags from heading text:
#HEADING_REGEX = re.compile("^(\*+) (.+?)(\w+:.+?:)?$")
HEADING_REGEX = re.compile("^(\*+) (.+?)$")

parser = argparse.ArgumentParser(description=DESCRIPTION,
                                 epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter,)

parser.add_argument('files', metavar='file', type=str, nargs='+',
                    help='a list of file names')

verbosity_group = parser.add_mutually_exclusive_group()
verbosity_group.add_argument("-v", "--verbose", action="store_true")
verbosity_group.add_argument("--quiet", action="store_true")
verbosity_group.add_argument('--version', action='version', version=PROG_VERSION)

args = parser.parse_args()

def handle_logging():
    """Log handling and configuration"""

    if args.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    elif args.quiet:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.ERROR, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)

    sys.exit(errorcode)

def sanitize_title(title):
    """
    @param title: string containing an org-mode title
    @param return: normalized and sanitized string
    """

    ## removing common strings:
    mapping = {' [#A] ':' ', ' [#B] ':' ', ' [#C] ':' ',
               'NEXT ':'', 'TODO ':'', 'STARTED ':'', 'DONE ':'', 'CANCELLED ':'', 'WAITING ':'', 'SOMEDAY ':''}

    for key, value in mapping.items():
        title = title.replace(key, value)

    if len(title) > 30:
        title = title[:30].strip()
    if len(title) == 30:
        title = title + '...'

    return title

def print_entry(filename, entry):
    print(str(entry['length']) + '	' + filename + '/' + '/'.join(entry['orgpath']) + '/' + entry['title'])

def handle_file(filename):
    """
    @param filename: string containing one file name
    @param return: data structure of parsed data
    """

    assert filename.__class__ == str or \
        filename.__class__ == unicode

    data = []
    current_line_number = 0
    previous_entry = []
    previous_level = 0
    current_path = []

    for line in open(filename, 'r'):
        current_line_number += 1
        components = HEADING_REGEX.match(line)
        if components:
            level = len(components.group(1))
            title = sanitize_title(components.group(2))

            if previous_level < level:
                ## FIXXME: this fails when previous_level differs more than one level
                #if previous_level > 0:
                #    print_entry(filename, data.pop())
                current_path.append(title)
            elif previous_level == level:
                data[-1]['length'] = current_line_number - data[-1]['length']
                current_path.pop()
                if previous_level > 0:
                    print_entry(filename, data.pop())
                current_path.append(title)
            elif previous_level > level:
                data[-1]['length'] = current_line_number - data[-1]['length']
                difference = previous_level - level
                for _ in range(difference):
                    print_entry(filename, data.pop())
                    current_path.pop()

            entry = {'level': level, 'line': current_line_number,
                     'title': title, 'length': current_line_number,
                     'orgpath': current_path}

            data.append(entry)
            previous_entry = entry
            previous_level = level
            #import pdb; pdb.set_trace()

    return data

def successful_exit():
    logging.debug("successfully finished.")
    sys.stdout.flush()
    sys.exit(0)


def main():
    """Main function"""

    files = args.files

    if len(files) < 1:
        print(os.path.basename(sys.argv[0]) + " version " + PROG_VERSION_DATE)
        parser.print_help()
        sys.exit(0)

    handle_logging()

    logging.debug("extracting list of files ...")
    logging.debug("files: %s" % str(files))

    logging.debug("%s filenames found: [%s]" % (str(len(files)), '], ['.join(files)))

    for filename in files:
        if not os.path.isfile(filename):
            logging.debug("file type error in folder [%s]: file type: is file? %s  -  is dir? %s  -  is mount? %s" % (os.getcwdu(), str(os.path.isfile(filename)), str(os.path.isdir(filename)), str(os.path.islink(filename))))
            logging.error("Skipping \"%s\" because this tool only processes existing file names." % filename)
        else:
            logging.debug("Happily processing file: \"%s\"" % filename)
            handle_file(filename)

    successful_exit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

# END OF FILE #################################################################

# end
