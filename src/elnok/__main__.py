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
from datetime import datetime
import logging
import requests
import sys
import time
from typing import Iterator

import elnok

from collections import OrderedDict

# Elasticsearch API described here:
# https://www.elastic.co/guide/en/elasticsearch/reference/current/search-search.html
# Example call
#curl -X GET "localhost:9200/logstash-*/_search?pretty" -H 'Content-Type: application/json' -d'
#                                 {
#                                   "query": {
#                                     "match_all": {}
#                                   }
#                                 }
#                                 '
#Example output
#{
# :
#  "hits" : {
# :
#    "hits" : [
#      {
#        "_index" : "logstash-2021.04.12-000001",
#        "_type" : "_doc",
#        "_id" : "XlzGxngBpKXm13z6qcO-",
#        "_score" : 1.0,
#        "_source" : {
#          "message" : "SIM: parsing *ESR?",
#          "component" : "odemis",
#          "module" : "WCPCM",
#          "level" : "DEBUG",
#          "host" : "ericaspire",
#          "timestamp" : "2021-04-12 14:57:46,306",
#          "subcomponent" : "lakeshore",
#          "path" : "/var/log/odemis.log",
#          "@timestamp" : "2021-04-12T12:57:46.306Z",
#          "@version" : "1",
#          "line" : "494",
#          "raw_message" : "2021-04-12 14:57:46,306\tDEBUG\tlakeshore:494:\tSIM: parsing *ESR?"
#        }
#      },
#  :
#}
# Comma-separated list of data streams, indices, and index aliases
TARGET="logstash-*"  # Hardcoded for now

# List of fields to show in the output, hard-coded for now
# No need to indicate the @timestamp, it's handled by default
OUTPUT = ["level", "module", "component", "subcomponent", "line", "message"]

HOST = "localhost:9200"  # Hard-coded for now

# SEARCH_URL =  "http://{host}/{target}/_search?"
SEARCH_URL = "http://{host}/{target}/_search?pretty"  # for debug

TIME_FMT = "%Y-%m-%d %H:%M:%S.%f"
OUTPUT_FMT = "{@timestamp}\t{level}\t{module}\t{component}\t{subcomponent}:{line}\t{message}"


def es_search(host: str, target: str, search: str=None) -> Iterator[str]:
    # TODO: add _source in query, to limit the fields returned
    # TODO: use "size" to have a longer query
    # TODO: to scroll through a large answer, use search_after, with pit and scrolls
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#search-after
    
    url = SEARCH_URL.format(host=host, target=target)
    req_data = {
        "sort": [{"@timestamp": "asc"}],
    }
    response = requests.get(url, json=req_data)
    # Use OrderedDict in order to keep the order
    for h in response.json(object_pairs_hook=OrderedDict)["hits"]["hits"]:
        yield h


def print_hit(hit: dict):
    source = hit["_source"]

    # Convert from timestamp -> epoch, and put it back into the user's format
    # example @timestamp: "2021-04-12T12:58:07.926Z"
    ts = datetime.strptime(source["@timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
    source["@timestamp"] = ts.strftime(TIME_FMT)

    print(OUTPUT_FMT.format(**source))
    

def main(args: list) -> int:
    # arguments handling
    parser = argparse.ArgumentParser(description="Elasticsearch/Logstash simple log displayer")

    parser.add_argument('--version', dest="version", action='store_true',
                        help="show program's version number and exit")
    parser.add_argument("--log-level", dest="loglev", metavar="<level>", type=int, choices=[0, 1, 2],
                         default=0, help="set verbosity level (0-2, default = 0)")

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

    for hit in es_search(HOST, TARGET):
        print_hit(hit)


    return 0

ret = main(sys.argv)
exit(ret)

