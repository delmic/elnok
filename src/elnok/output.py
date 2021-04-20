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
from datetime import datetime
import json
import logging
import string

TIME_FMT = "%Y-%m-%d %H:%M:%S.%f"
# OUTPUT_FMT = "{@timestamp}\t{level}\t{module}\t{component}\t{subcomponent}:{line}\t{message}"


class DefaultFormatter(string.Formatter):
    """
    String formatter which replaces missing keys by no text
    """
    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except KeyError:
            logging.info("Missing field %s", key)
            return ""


def print_hit(hit: dict, fmt: str):
    source = hit["_source"]

    # Convert from timestamp -> epoch, and put it back into the user's format
    # example @timestamp: "2021-04-12T12:58:07.926Z"
    # TODO: do it lazyly in the formater
    if "@timestamp" in source:
        ts = datetime.strptime(source["@timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
        source["@timestamp"] = ts.strftime(TIME_FMT)

    # TODO: handle better if a field is missing (than KeyError)
    # => represent the field as empty (this really happens in logstash, if the field is empty)
    formatter = DefaultFormatter()
    try:
        print(formatter.format(fmt, **source))
    except KeyError:
        logging.exception("Failed to print %s", source)
        raise


def print_json_raw(hit: dict, fmt: str):
    """
    fmt: unused
    """
    source = hit["_source"]
    try:
        print(json.dumps(source))
    except KeyError:
        logging.exception("Failed to print %s", source)
        raise
