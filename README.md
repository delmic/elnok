# ELnoK: A light front-end to Logstash/Elasticsearch

ELnoK stands for "Elasticsearch-Logstash-no Kibana". It was created to fulfil
some needs to inspect logs stored in Elasticsearch without having to rely on the
Kibana web interface.

It's a very simple tool to just output the logs lines corresponding to a specific
time period and/or strings matches in the fields. In practice, it can be handy if
you use Logstash and Elasticsearch to merge many logs together, and output them
synchronized, all in the same format.

## Environment
Requires Python 3.6+, and the "requests" Python package.
Tested only on Ubuntu 18.04, but probably will work on any Linux system, and could
even work on Windows.

## Installation
```
pip3 install -r requirements.txt
python3 setup.py build
sudo python3 setup.py install
```

Note, that alternatively, you can start elnok without installing it, using such lines:
```
export PYTHONPATH="src/"
python3 -m elnok ....
```

## Usage
On Linux, you can use the script `elnok` to run it. Note that it's inspired by
the journalctl command, so you might find familiar behaviour.
elnok [OPTIONS...] [MATCHES....]

### MATCHES
By default, it will list all the log. By specifying field matches, you can filter
the output so that the given fields of the log must contain at least the given
word. Matches are written in the format "field=value". Several matches can be
passed. In the case different fields are passed, all the matches will have to match.

### OPTIONS
* -h, --help

    Show a help message and exit

* --version

    Show program's version number and exit

* --log-level <level>

    Set verbosity level (0-3, default = 0) of the elnok internals. 0 only shows errors.
    A higher number shows more information about the program's behaviour.
    Everything is logged on the error output. Unless you're debugging an issue
    with elnok, you probably want to leave it to the minimum.

* --host HOST

    Specify the name or IP address and port of the Elasticsearch server (default is localhost:9200).

* --index INDEX

    Specify the index pattern to look into (default is logstash-*). It can be comma separated.

* -o, --output OUTPUT

    Controls the format of the generated output. Accepts "short" or "json".
    The default is "short", which outputs each log on a line, tab/semicolon separated.
    "json" shows each log line as a raw Elasticsearch hit

* --output-fields FIELDS

    List of the fields to be printed (comma/semicolon separated).
    On "json" output, by default all the fields are shown. On "short", the default
    is  "@timestamp,level,module,component,subcomponent:line,message". Commas are
    replaced by tabs, and semicolons stay as is.
    The fields available depend on the logstash storage. To find out the available ones,
    use the json output, with the default behaviour.

* -S, --since SINCE, -U, --until UNTIL

    Show entries within a limited period. SINCE is used to select the starting date
    (by default is starts with the oldest log available). UNTIL is used to select
    the last date shown. The date format follows Elasticsearch's format.
    It can be either a full date like "2012-10-30 18:17:16", or can be a relative
    date like "now-2d" or "now-1h". For a full description, see the
    [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-daterange-aggregation.html)
    [definitions](https://www.elastic.co/guide/en/elasticsearch/reference/current/common-options.html).


### Example

Shows all the log available:

        elnok

Store the log of 2 days ago into a file:

        elnok --log-level 1 -S now-2d/d -U now-1d/d > two-days-ago.log

Shows all log of the last 60 minutes with the ERROR level:

        elnok -S now-1h level=ERROR

Shows only the log where the field "subcomponent" is "img", and output a very short display:

        elnok -S now-5d -U now --output-fields @timestamp,level,message subcomponent=img

Shows the latest minutes logs in raw JSON format:

        elnok -S now-1m --output json
