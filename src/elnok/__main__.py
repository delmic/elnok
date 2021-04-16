# -*- coding: utf-8 -*-
'''
Created on 12 Apr 2021

@author: Éric Piel

Copyright © 2021 Éric Piel, Delmic

This file is part of ELnoK.

ELnoK is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License version 2 as published by the Free Software
Foundation.

ELnoK is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
ELnoK. If not, see http://www.gnu.org/licenses/.
'''

# Syntax is inspired by journalctl.
# Call like:
# elnok [OPTIONS...] [MATCHES...]
# -S, --since=, -U, --until=

import argparse
import logging
import sys

from elnok import es, output
import elnok


# Comma-separated list of data streams, indices, and index aliases
TARGET="logstash-*"  # Hardcoded for now

# List of fields to show in the output, hard-coded for now
# No need to indicate the @timestamp, it's handled by default
OUTPUT = ["level", "module", "component", "subcomponent", "line", "message"]

HOST = "localhost:9200"  # Hard-coded for now



def main(args: list) -> int:
    # arguments handling
    parser = argparse.ArgumentParser(description="Elasticsearch/Logstash simple log displayer")

    parser.add_argument('--version', dest="version", action='store_true',
                        help="show program's version number and exit")
    parser.add_argument("--log-level", dest="loglev", metavar="<level>", type=int, choices=[0, 1, 2],
                         default=0, help="set verbosity level (0-2, default = 0)")
    parser.add_argument("--since", "-S", dest="since",
                        help="Show entries on or newer than the given date. Format is 2012-10-30 18:17:16 or now-2d.")
    parser.add_argument("--until", "-U", dest="until",
                        help="Show entries on or before the given date. Format is 2012-10-30 18:17:16 or now-1h.")
    parser.add_argument("match", nargs="*",
                        help="Filter the output to only the fields that match")

    options = parser.parse_args(args[1:])

    # Cannot use the internal feature, because it doesn't support multiline
    if options.version:
        print(elnok.__shortname__ + " " + elnok.__version__ + "\n" +
              elnok.__copyright__ + "\n" +
              "Licensed under the " + elnok.__license__)
        return 0

    # Set up logging before everything else
    loglev_names = [logging.WARNING, logging.INFO, logging.DEBUG]
    loglev = loglev_names[options.loglev]

    # change the log format to be more descriptive
    logging.basicConfig(level=loglev, format='%(asctime)s (%(module)s) %(levelname)s: %(message)s')

    # Convert matches from field=value to a dict field -> value
    matches = {}
    for m in options.match:
        field, value = m.split("=")
        # TODO: support multiple times the same field (as a OR)
        matches[field] = value

    for hit in es.search(HOST, TARGET, match=matches, since=options.since, until=options.until):
        output.print_hit(hit)

    return 0

ret = main(sys.argv)
exit(ret)

