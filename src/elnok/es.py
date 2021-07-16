# -*- coding: utf-8 -*-
'''
Created on 16 Apr 2021

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
from collections import OrderedDict
import logging
import requests
from typing import Optional, Iterator, Dict, List, Set

# Elasticsearch API described here:
# https://www.elastic.co/guide/en/elasticsearch/reference/current/search-search.html
# Example call
# curl -X GET "localhost:9200/logstash-*/_search?pretty" -H 'Content-Type: application/json' -d'
#                                 {
#                                   "query": {
#                                     "match_all": {}
#                                   }
#                                 }
#                                 '
# Example output
# {
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
# }
# SEARCH_URL =  "http://{host}/{target}/_search?"
SEARCH_MULTI_URL = "http://{host}/_search"
PIT_URL = "http://{host}/{target}/_pit"


def get_pit(host:str, target: str, keep_alive:float=60) -> dict:
    """
    keep_alive: how long the PIT should be valid (s)
    """

    url = PIT_URL.format(host=host, target=target)
    response = requests.post(url, params={"keep_alive": "%ds" % keep_alive})
    logging.debug(response.text)
    return response.json()["id"]


def search(host: str, target: str, match: Optional[Dict[str, str]]=None,
              since: Optional[str]=None, until: Optional[str]=None,
              fields: Optional[Set[str]]=None
              ) -> Iterator[dict]:
    """
    Does a elasticsearch query, by returning each hit one at a time via an iterator
    match: a mapping of field -> a filter on what to return. It follows the syntax of 
      ElasticSearch "match" query. See:
      https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
    since: filter for the minimum time
    until: filter for the maximum time. For the format. See:
      https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-daterange-aggregation.html
    fields: restrict the fields to return in the hit
    yield: dict (str -> value): each result (hit) found, in time ascending order
    """
    # TODO: add _source in query, to limit the fields returned
    # We don't receive a single "endless" response. Instead, we start a search,
    # and then "scroll" through it, by asking for more results. See:
    # https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html

    # Get a "Point-in-time" (PIT), which is a sort of pointer to a snapshot of
    # the log, so that even if data changes, the paginated results don't change.
    pit = get_pit(host, target, keep_alive=10)

    # Keep requesting small amounts of data
    hits = None
    while True:
        url = SEARCH_MULTI_URL.format(host=host, target=target)
        req_data = {
            # Can be up to 10000. Any number "works", but too small cause a lot
            # of overhead, and too big causes latency.
            "size": 1000,
            "sort": [{"@timestamp": "asc"}],
            "pit": {"id": pit,
                    "keep_alive": "10s",  # Extend the PIT duration
            },
        }
        
        # Due to elasticsearch being a search engine, the query syntax is very
        # sophisticated. To look for multiple criteria (eg field match and time range),
        # it's necessary to combine them via a "bool,filter" query, which just
        # means all the criteria have to be fullfiled.
        # Note that it's fine to run a query with an empty filter.
        q_filters = []
        req_data["query"] = {
            "bool": {
                "filter": q_filters
            }
        }

        for field, val in match.items():
            # There are many types of text search "term" is looking for exactly the value
            # There might be better or more flexible options with match, wildcard or regexp...
            # https://www.elastic.co/guide/en/elasticsearch/reference/7.13/query-dsl-wildcard-query.html
            # q_filters.append({"wildcard": {field: {"value": val}}})
            # TODO: if the field is repeated, extend the query to work as a OR (ie, separate words with a space)
            q_filters.append({"match": {field: {"query": val}}})
            # TODO make the query case sensitive. It should be the matter of selecting
            # the right analyzer.
            # https://www.elastic.co/guide/en/elasticsearch/reference/current/specify-analyzer.html
            # However, for now adding "analyzer": "whitespace" seems to only make
            # the query text as-is, while the fields are always lowercase...

        # Add a time range, if requested. See:
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-range-query.html
        q_time = {}
        if since:
            q_time["gte"] = since
        if until:
            q_time["lte"] = until

        if q_time:
            q_filters.append({"range": {"@timestamp": q_time}})

        # TODO: report properly if the date format is incorrect (ie, not understood by ES)

        if fields is not None:
            req_data["_source"] = list(fields)

        # Pass info from the previous request (if it's not the first one)
        if hits is not None:
            req_data["search_after"] = hits[-1]["sort"]

        logging.debug("%s", req_data)
        response = requests.get(url, json=req_data)
        logging.debug(response.text)

        # Use OrderedDict in order to keep the order
        resp_dict = response.json(object_pairs_hook=OrderedDict)

        # In case there was an error parsing the query, it'll return "error" instead of "hits"
        if not "hits" in resp_dict:
            logging.error("Search query failed")
            if "error" in resp_dict:
                # TODO: make it prettier (it should be some kind of recursive text?
                for field, value in resp_dict["error"].items():
                    print("%s: %s" % (field, value))
            return

        hits = resp_dict["hits"]["hits"]
        if not hits:  # End of the search?
            return

        # Pass one each log line, one at a time
        for h in hits:
            yield h

