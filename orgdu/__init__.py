#!/usr/bin/env python3
# -*- coding: utf-8 -*-
PROG_VERSION = u"Time-stamp: <2017-03-26 19:12:09 vk>"

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

EPILOG = u"Verbose description: http://Karl-Voit.at/2017/03/27/org-du/\n\
\n\
:copyright: (c) by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v3 or any later version\n\
:URL: https://github.com/novoid/org-du\n\
:bugreports: via github or <tools@Karl-Voit.at>\n\
:version: " + PROG_VERSION_DATE + "\n"


# FIXXME: separate tags from heading text:
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

    # removing common strings:
    mapping = {' [#A] ': ' ', ' [#B] ': ' ', ' [#C] ': ' ',
               'NEXT ': '', 'TODO ': '', 'STARTED ': '', 'DONE ': '', 'CANCELLED ': '', 'WAITING ': '', 'SOMEDAY ': '',
               '/': '⋅'}

    for key, value in mapping.items():
        title = title.replace(key, value)

    if len(title) > 30:
        title = title[:30].strip()
    if len(title) == 30:
        title = title + '...'

    return title


def handle_files(files):
    """iteration function for handling all the files from the command line argument"""

    for filename in files:
        if not os.path.isfile(filename):
            logging.debug("file type error in folder [%s]: file type: is file? %s  -  is dir? %s  -  is mount? %s" %
                          (os.getcwdu(), str(os.path.isfile(filename)), str(os.path.isdir(filename)), str(os.path.islink(filename))))
            logging.error("Skipping \"%s\" because this tool only processes existing file names." % filename)
        else:
            logging.debug("Happily processing file: \"%s\"" % filename)
            handle_file(filename)


class OrgTree:
    """Data access object (DAO) for Org-mode headings"""

    data = []
    filename = ""

    def __init__(self, filename):
        self.data = []
        self.filename = filename

    def get_heading_path(self):
        """derive the absolute path of the current heading with all its ancestor headings"""
        path = ""
        for heading in self.data:
            path += '/' + heading['heading']
        return path

    def print_stack(self):
        """print the current status of the stack for debug purposes"""
        if args.verbose:
            print('\n')
            print("{0:10s} {1:5s}  {2}".format('started at', 'level', 'heading'))
            for entry in self.data:
                print("{0:10d} {1:5d}  {2}".format(entry['startinglinenumber'], entry['headinglevel'], entry['heading']))

    def print_top(self):
        """return the top entry of the stack"""
        assert self.data
        entry = self.top()
        print(str(entry['linecount']) + '	' + self.filename + self.get_heading_path())

    def push_linecount(self, currentlinenumber):
        """set the line count for the topmost entry"""

        assert 'linecount' not in self.data[-1].keys()
        self.data[-1]['linecount'] = currentlinenumber - self.data[-1]['startinglinenumber']

    def push(self, currentlinenumber, headinglevel, heading):
        """push a new heading to the stack, handling the pop-things when new level is smaller than the previous one(s)"""

        while self.top()['headinglevel'] >= headinglevel:
            self.push_linecount(currentlinenumber)
            self.print_top()
            self.pop()
        self.data.append({'startinglinenumber': currentlinenumber, 'headinglevel': headinglevel, 'heading': heading})
        self.print_stack()

    def pop(self):
        """pops the topmost item"""

        assert len(self.data) > 0
        return self.data.pop()

    def flush(self, currentlinenumber):
        """when the input file has ended, flush the stack"""

        while self.top()['headinglevel'] > 0:
            self.push_linecount(currentlinenumber)
            self.print_top()
            self.pop()

    def top(self):
        """return the topmost stack entry"""
        if len(self.data) > 0:
            return self.data[-1]
        else:
            return {'startinglinenumber': 0, 'headinglevel': 0, 'heading': self.filename}


def handle_file(filename):
    """
    @param filename: string containing one file name
    @param return: data structure of parsed data
    """

    assert filename.__class__ == str or \
        filename.__class__ == unicode

    current_line_number = 0
    orgtree = OrgTree(filename)

    for line in open(filename, 'r'):
        current_line_number += 1
        components = HEADING_REGEX.match(line)
        # if components are found, we have found a new heading:
        if components:
            level = len(components.group(1))
            heading = sanitize_title(components.group(2))
            orgtree.push(current_line_number, level, heading)

    orgtree.flush(current_line_number)

    print(str(current_line_number) + '	' + filename)

    return current_line_number


def successful_exit():
    """handles the successful finish of this tool"""
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

    handle_files(files)

    successful_exit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

# END OF FILE #################################################################

# end
