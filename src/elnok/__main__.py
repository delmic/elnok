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
# Call like :
# elnok [OPTIONS...] [MATCHES...]
# -S, --since=, -U, --until=

import argparse
import logging
import re
import sys
from typing import Set

from elnok import es, output
import elnok

DEFAULT_OUTPUT_SHORT = "@timestamp,level,module,component,subcomponent:line,message"


def main(args: list) -> int:
    # arguments handling
    parser = argparse.ArgumentParser(description="A light front-end to Logstash/Elasticsearch")

    parser.add_argument('--version', dest="version", action='store_true',
                        help="Show program's version number and exit")
    parser.add_argument("--log-level", dest="loglev", metavar="<level>", type=int, choices=[0, 1, 2, 3],
                        default=0, help="Set verbosity level (0-3, default = 0) of the elnok internals")
    parser.add_argument("--host", default="localhost:9200",
                        help="Specify the name or IP address and port of the elasticsearch server (default is localhost:9200)")
    parser.add_argument("--index", default="logstash-*",
                        help="Specify the index pattern to look into (default is logstash-*). It can be comma separated.")
    parser.add_argument("--list-fields", dest="list", action='store_true',
                        help="List all the fields present in the index (tab separated)")
    parser.add_argument("--output", "-o", dest="output", default="short", choices=["short", "json"],
                        help="Controls the format of the generated output.\n "
                        "Default is short, which outputs each log on a line, tab/semicolon separated.\n "
                        "json shows each log line as a raw elasticsearch hit")
    parser.add_argument("--output-fields", dest="fields",
                        help="List of the fields to be printed (comma/semicolon separated)")
    parser.add_argument("--since", "-S", dest="since",
                        help="Show entries on or newer than the given date. Format is 2012-10-30T18:17:16 or now-2d.")
    parser.add_argument("--until", "-U", dest="until",
                        help="Show entries on or before the given date. Format is 2012-10-30T18:17:16 or now-1h.")
    parser.add_argument("matches", nargs="*",
                        help="Filter the output to only the fields that match")

    options = parser.parse_args(args[1:])

    # Cannot use the internal feature, because it doesn't support multiline
    if options.version:
        print(elnok.__shortname__ + " " + elnok.__version__ + "\n" +
              elnok.__copyright__ + "\n" +
              "Licensed under the " + elnok.__license__)
        return 0

    # Set up logging before everything else
    loglev_names = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    loglev = loglev_names[options.loglev]

    # change the log format to be more descriptive
    logging.basicConfig(level=loglev, format='%(asctime)s (%(module)s) %(levelname)s: %(message)s')

    try:
        if options.list:
            fields_names = es.list_fields(options.host, options.index)
            print("\t".join(sorted(fields_names)))
            return 0

        # Convert matches from field=value to a dict field -> value
        matches = {}
        for m in options.matches:
            field, value = m.split("=")
            # TODO: support multiple times the same field (as a OR)
            if field in matches:
                raise ValueError("Cannot pass multiple matches on the same field (%s)" % (field,))
            matches[field] = value

        # Create the set of fields to retrieve
        if options.fields is None:
            # Pick different default fields based on output format
            if options.output == "short":
                options.fields = DEFAULT_OUTPUT_SHORT
            # For "json", we leave "None", which means all the fields

        fields = None  # all
        if options.fields:
            fields = set(f for f in re.split("[,:]", options.fields) if f)

        logging.debug("Selected fields are: %s", fields)

        # Create the formatting of the output, from the fields
        fields_fmt = None
        if options.fields:
            fields_fmt = []
            # Replace , -> \t and : stays :.
            # Each field is surrounded by {}.
            for m in re.finditer("[,:]+|[^,:]+", options.fields):
                p = m.group(0)
                # p is either a series of ,:, or a field name
                if not p:  # This shouldn't happen
                    logging.warning("Empty token %s", m)
                elif p[0] == ",":
                    fields_fmt.append("\t")
                elif p[0] == ":":
                    fields_fmt.append(":")
                else:
                    fields_fmt.append("{%s}" % (p,))

            fields_fmt = "".join(fields_fmt)

        logging.debug("Field format: %s", fields_fmt)

        if options.output == "short":
            print_output = output.print_hit
        elif options.output == "json":
            print_output = output.print_json_raw
        else:
            raise ValueError("Unknown output %s" % options.output)

        no_matches = True
        hit_fields: Set[str] = set()  # all the fields returned by the search
        for hit in es.search(options.host, options.index, match=matches, since=options.since, until=options.until, fields=fields):
            no_matches = False
            hit_fields.update(hit.get("_source", {}).keys())
            print_output(hit, fields_fmt)

        # If one of the fields to output was *never* returned, it might be that
        # there is a mistake in the field names to output. As it's easy to check,
        # we do it and report a error in this case.
        logging.debug("hit fields = %s, vs %s", hit_fields, fields)
        if fields:
            always_empty_fields = fields - hit_fields
            logging.debug("empty fields = %s", always_empty_fields)
            if always_empty_fields:
                fields_available = set(es.list_fields(options.host, options.index))
                wrong_fields = always_empty_fields - fields_available
                if wrong_fields:
                    logging.error("These fields do not exists: %s", ", ".join(sorted(wrong_fields)))
                    return 1

        # If nothing found, and the user has passed some matches, it could be that
        # there was a mistake in the field names of the matches. As it's easy to check, we do it and
        # report an "error" in this case.
        if no_matches and matches:
            # Something is strange => check if the user selected a field which doesn't exists
            fields_available = set(es.list_fields(options.host, options.index))
            wrong_fields = set(matches.keys()) - fields_available
            if wrong_fields:
                logging.error("These fields do not exists: %s", ", ".join(sorted(wrong_fields)))
                return 1

    except KeyboardInterrupt:  # Stopped by user
        logging.debug("Execution interrupted")
        return 128
    except Exception:
        logging.exception("Failure during execution")
        return 1

    return 0

ret = main(sys.argv)
exit(ret)

