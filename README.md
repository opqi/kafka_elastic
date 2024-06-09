# Streaming data from Kafka to Elasticsearch using Kafka Connect Elasticsearch Sink


![kafka to elasticsearch cover](kafka-to-elasticsearch-cover.jpg)

------------------------------------------------------------------------

🎥 **Check out the video tutorial here:
[https://rmoff.dev/kafka-elasticsearch-video](https://rmoff.dev/kafka-elasticsearch-video)**

------------------------------------------------------------------------

This demo uses Docker and Docker Compose to provision the stack, but all
you actually need for getting data from Kafka to Elasticsearch is Apache
Kafka and the [Kafka Connect Elasticsearch Sink
connector](https://www.confluent.io/hub/confluentinc/kafka-connect-elasticsearch).
It also uses ksqlDB as an easy interface for producing/consuming from
Kafka topics, and creating Kafka Connect connectors - but you don't have
to use it in order to use Kafka Connect.
## Getting started {#_getting_started}

1.  Bring the Docker Compose up

    ``` highlight
    docker-compose up -d
    ```

2.  Make sure everything is up and running

    ``` highlight
    ➜ docker-compose ps
         Name                    Command                  State                    Ports
    --------------------------------------------------------------------------------------------------
    broker            /etc/confluent/docker/run        Up             0.0.0.0:9092->9092/tcp
    elasticsearch     /usr/local/bin/docker-entr ...   Up             0.0.0.0:9200->9200/tcp, 9300/tcp
    kafka-connect     bash -c echo "Installing c ...   Up (healthy)   0.0.0.0:8083->8083/tcp, 9092/tcp
    kafkacat          /bin/sh -c apk add jq;           Up
                      wh ...
    kibana            /usr/local/bin/dumb-init - ...   Up             0.0.0.0:5601->5601/tcp
    ksqldb            /usr/bin/docker/run              Up             0.0.0.0:8088->8088/tcp
    schema-registry   /etc/confluent/docker/run        Up             0.0.0.0:8081->8081/tcp
    zookeeper         /etc/confluent/docker/run        Up             2181/tcp, 2888/tcp, 3888/tcp
    ```
    Wait for ksqlDB and Kafka Connect

    ``` highlight
    echo -e "\n\n=============\nWaiting for Kafka Connect to start listening on localhost ⏳\n=============\n"
    while [ $(curl -s -o /dev/null -w %{http_code} http://localhost:8083/connectors) -ne 200 ] ; do
      echo -e "\t" $(date) " Kafka Connect listener HTTP state: " $(curl -s -o /dev/null -w %{http_code} http://localhost:8083/connectors) " (waiting for 200)"
      sleep 5
    done
    echo -e $(date) "\n\n--------------\n\o/ Kafka Connect is ready! \n--------------\n"

    docker exec -it ksqldb bash -c 'echo -e "\n\n⏳ Waiting for ksqlDB to be available before launching CLI\n"; while : ; do curl_status=$(curl -s -o /dev/null -w %{http_code} http://ksqldb:8088/info) ; echo -e $(date) " ksqlDB server listener HTTP state: " $curl_status " (waiting for 200)" ; if [ $curl_status -eq 200 ] ; then  break ; fi ; sleep 5 ; done ; ksql http://ksqldb:8088'
    ```
## Kibana connect to Elastic

```docker exec -it elasticsearch bin/elasticsearch-service-tokens create elastic/kibana kibana_token```

Paste the token to the kibana.yml

## Basics

[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&feature=youtu.be)

::: {.olist .arabic}
1.  Create test topic + data using ksqlDB (but it's still just a Kafka
    topic under the covers)

    ``` highlight
    docker exec -it ksqldb ksql http://ksqldb:8088
    ```
    
    ``` highlight
    CREATE STREAM TEST01 (ALPHA VARCHAR KEY,COL1 INT, COL2 VARCHAR)
      WITH (KAFKA_TOPIC='test01', PARTITIONS=1, FORMAT='AVRO');
    ```
    
    ``` highlight
    INSERT INTO TEST01 (ALPHA, COL1, COL2) VALUES ('X',1,'FOO');
    INSERT INTO TEST01 (ALPHA, COL1, COL2) VALUES ('Y',2,'BAR');
    ```
    ``` highlight
    SHOW TOPICS;
    PRINT test01 FROM BEGINNING LIMIT 2;
    ```
    ``` highlight
     Kafka Topic                           | Partitions | Partition Replicas
    -------------------------------------------------------------------------
     confluent_rmoff_01ksql_processing_log | 1          | 1
     test01                                | 1          | 1
    -------------------------------------------------------------------------
    Key format: AVRO or KAFKA_STRING
    Value format: AVRO or KAFKA_STRING
    rowtime: 2021/02/18 15:38:38.411 Z, key: X, value: {"COL1": 1, "COL2": "FOO"}, partition: 0
    rowtime: 2021/02/18 15:38:38.482 Z, key: Y, value: {"COL1": 2, "COL2": "BAR"}, partition: 0
    Topic printing ceased
    ksql>
    ```
    
2.  Stream the data to Elasticsearch with Kafka Connect

    I'm using ksqlDB to create the connector but you can use the Kafka
    Connect REST API directly if you want to. Kafka Connect is part of
    Apache Kafka and you don't have to use ksqlDB to use Kafka Connect.
    ``` highlight
    CREATE SINK CONNECTOR SINK_ELASTIC_TEST_01 WITH (
      'connector.class'                     = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
      'connection.url'                      = 'http://elasticsearch:9200',
      'value.converter'                     = 'io.confluent.connect.avro.AvroConverter',
      'value.converter.schema.registry.url' = 'http://schema-registry:8081',
      'key.converter'                       = 'io.confluent.connect.avro.AvroConverter',
      'key.converter.schema.registry.url'   = 'http://schema-registry:8081',
      'type.name'                           = '_doc',
      'topics'                              = 'test01',
      'key.ignore'                          = 'true',
      'schema.ignore'                       = 'false'
    );
    ```
    
3.  Check the data in Elasticsearch

    ``` highlight
    curl -s http://localhost:9200/test01/_search \
        -H 'content-type: application/json' \
        -d '{ "size": 42  }' | jq -c '.hits.hits[]'
    ```
    ``` highlight
    {"_index":"test01","_type":"_doc","_id":"test01+0+1","_score":1,"_source":{"COL1":2,"COL2":"BAR"}}
    {"_index":"test01","_type":"_doc","_id":"test01+0+0","_score":1,"_source":{"COL1":1,"COL2":"FOO"}}
    ```
    Check the mapping
    ``` highlight
    curl -s http://localhost:9200/test01/_mapping | jq '.'
    ```
    ``` highlight
    {
      "test01": {
        "mappings": {
          "properties": {
            "COL1": {
              "type": "integer"
            },
            "COL2": {
              "type": "text",
              "fields": {
                "keyword": {
                  "type": "keyword",
                  "ignore_above": 256
                }
              }
            }
          }
        }
      }
    }
    ```
    
## Key handling {#_key_handling}

### Updating documents in Elasticsearch {#_updating_documents_in_elasticsearch}

[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=437s)
1.  But where did our `ALPHA` key column go? And what happens if we
    insert new data against the same key and a new one?

    ``` highlight
    -- New key ('Z')
    INSERT INTO TEST01 (ALPHA, COL1, COL2) VALUES ('Z',1,'WOO');
    -- New value for existing key ('Y')
    INSERT INTO TEST01 (ALPHA, COL1, COL2) VALUES ('Y',4,'PFF');
    ```
    Elasticsearch:

    ``` highlight
    curl -s http://localhost:9200/test01/_search \
        -H 'content-type: application/json' \
        -d '{ "size": 42  }' | jq -c '.hits.hits[]'
    ```
    ``` highlight
    {"_index":"test01","_type":"_doc","_id":"test01+0+1","_score":1,"_source":{"COL1":2,"COL2":"BAR"}}
    {"_index":"test01","_type":"_doc","_id":"test01+0+0","_score":1,"_source":{"COL1":1,"COL2":"FOO"}}
    {"_index":"test01","_type":"_doc","_id":"test01+0+3","_score":1,"_source":{"COL1":4,"COL2":"PFF"}}
    {"_index":"test01","_type":"_doc","_id":"test01+0+2","_score":1,"_source":{"COL1":1,"COL2":"WOO"}}
    ```
    Note that the `_id` is made up of `<topic><partition><offset>`,
    which we can prove with kafkacat:
    ``` highlight
    docker exec kafkacat kafkacat \
            -b broker:29092 \
            -r http://schema-registry:8081 -s avro \
            -C -o beginning -e -q \
            -t test01 \
            -f 'Topic+Partition+Offset: %t+%p+%o\tKey: %k\tValue: %s\n'
    ```
    ``` highlight
    Topic+Partition+Offset: test01+0+0      Key: "X"  Value: {"COL1": {"int": 1}, "COL2": {"string": "FOO"}}
    Topic+Partition+Offset: test01+0+1      Key: "Y"  Value: {"COL1": {"int": 2}, "COL2": {"string": "BAR"}}
    Topic+Partition+Offset: test01+0+2      Key: "Z"  Value: {"COL1": {"int": 1}, "COL2": {"string": "WOO"}}
    Topic+Partition+Offset: test01+0+3      Key: "Y"  Value: {"COL1": {"int": 4}, "COL2": {"string": "PFF"}}
    ```

2.  Let's recreate the connector and use the Kafka message key as the
    document ID to enable updates & deletes against existing documents.

    -   ksqlDB - drop the connector

        -   `DROP CONNECTOR SINK_ELASTIC_TEST_01;`

    -   bash - delete the existing index in Elasticsearch (drop the
        connector first otherwise you'll see the index get recreated)

        -   `docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test01"`

    -   In ksqlDB create the connector as before but with
        `key.ignore=false`.

        +-----------------------------------+-----------------------------------+
        | ::: title                         | The connector is given a new      |
        | Note                              | name. If you give it the same as  |
        | :::                               | before then Kafka Connect will    |
        |                                   | assume it's the same connector    |
        |                                   | and not re-send any of the        |
        |                                   | existing records.                 |
        +-----------------------------------+-----------------------------------+
        :::

        :::: listingblock
        ::: content
        ``` highlight
        CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02 WITH (
          'connector.class'                     = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
          'connection.url'                      = 'http://elasticsearch:9200',
          'value.converter'                     = 'io.confluent.connect.avro.AvroConverter',
          'value.converter.schema.registry.url' = 'http://schema-registry:8081',
          'key.converter'                       = 'io.confluent.connect.avro.AvroConverter',
          'key.converter.schema.registry.url'   = 'http://schema-registry:8081',
          'type.name'                           = '_doc',
          'topics'                              = 'test01',
          'key.ignore'                          = 'false',
          'schema.ignore'                       = 'false'
        );
        ```
        :::
        ::::

        ::: paragraph
        Check the new data in Elasticsearch:
        :::

        :::: listingblock
        ::: content
        ``` highlight
        curl -s http://localhost:9200/test01/_search \
            -H 'content-type: application/json' \
            -d '{ "size": 42  }' | jq -c '.hits.hits[]'
        ```
        :::
        ::::

        :::: listingblock
        ::: content
        ``` highlight
        {"_index":"test01","_type":"_doc","_id":"X","_score":1,"_source":{"COL1":1,"COL2":"FOO"}}
        {"_index":"test01","_type":"_doc","_id":"Y","_score":1,"_source":{"COL1":4,"COL2":"PFF"}}
        {"_index":"test01","_type":"_doc","_id":"Z","_score":1,"_source":{"COL1":1,"COL2":"WOO"}}
        ```
        :::
        ::::

        ::: paragraph
        Note that `_id` now maps the key of the Kafka message, and that
        the value for message key/document id `Y` has been updated in
        place. Here's the data in the Kafka topic in ksqlDB:
        :::

        :::: listingblock
        ::: content
        ``` highlight
        ksql> SET 'auto.offset.reset' = 'earliest';
        ksql> SELECT ALPHA, COL1, COL2 FROM TEST01 EMIT CHANGES LIMIT 4;
        ```
        :::
        ::::

        :::: listingblock
        ::: content
        ``` highlight
        +-------+------+-----+
        |ALPHA  |COL1  |COL2 |
        +-------+------+-----+
        |X      |1     |FOO  |
        |Y      |2     |BAR  |
        |Z      |1     |WOO  |
        |Y      |4     |PFF  |
        ```
        :::
        ::::
    :::
:::
:::::

::::::::::::::::::::::::::::::::: sect2
### Deleting documents in Elasticsearch with Tombstone messages {#_deleting_documents_in_elasticsearch_with_tombstone_messages}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=698s)
:::

::: paragraph
What about deletes? We can do those too, using tombstone (null value)
messages. By default the connector will ignore these but [there's an
option](https://docs.confluent.io/current/connect/kafka-connect-elasticsearch/configuration_options.html#data-conversion)
to process them as deletes - `behavior.on.null.values`.
:::

::: ulist
-   ksqlDB - drop the connector

    :::: listingblock
    ::: content
    ``` highlight
    DROP CONNECTOR SINK_ELASTIC_TEST_02;
    ```
    :::
    ::::

-   bash - delete the existing index in Elasticsearch (drop the
    connector first otherwise you'll see the index get recreated)

    :::: listingblock
    ::: content
    ``` highlight
    docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test01"
    ```
    :::
    ::::
:::

::: paragraph
In ksqlDB create the connector as before but with
`behavior.on.null.values=delete`.
:::

::: {.admonitionblock .note}
+-----------------------------------+-----------------------------------+
| ::: title                         | The connector is given a new      |
| Note                              | name. If you give it the same as  |
| :::                               | before then Kafka Connect will    |
|                                   | assume it's the same connector    |
|                                   | and not re-send any of the        |
|                                   | existing records.                 |
+-----------------------------------+-----------------------------------+
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_03 WITH (
  'connector.class'                     = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'                      = 'http://elasticsearch:9200',
  'value.converter'                     = 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url' = 'http://schema-registry:8081',
  'key.converter'                       = 'io.confluent.connect.avro.AvroConverter',
  'key.converter.schema.registry.url'   = 'http://schema-registry:8081',
  'type.name'                           = '_doc',
  'topics'                              = 'test01',
  'key.ignore'                          = 'false',
  'schema.ignore'                       = 'false',
  'behavior.on.null.values'             = 'delete'
);
```
:::
::::

::: paragraph
Remind ourselves of source data in ksqlDB:
:::

:::: listingblock
::: content
``` highlight
PRINT test01 FROM BEGINNING;
```
:::
::::

:::: listingblock
::: content
``` highlight
rowtime: 4/30/20 4:24:12 PM UTC, key: X, value: {"COL1": 1, "COL2": "FOO"}
rowtime: 4/30/20 4:24:12 PM UTC, key: Y, value: {"COL1": 2, "COL2": "BAR"}
rowtime: 4/30/20 4:24:19 PM UTC, key: Z, value: {"COL1": 1, "COL2": "WOO"}
rowtime: 4/30/20 4:24:19 PM UTC, key: Y, value: {"COL1": 4, "COL2": "PFF"}
```
:::
::::

::: paragraph
Current Elasticsearch state:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test01/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test01","_type":"_doc","_id":"X","_score":1,"_source":{"COL1":1,"COL2":"FOO"}}
{"_index":"test01","_type":"_doc","_id":"Y","_score":1,"_source":{"COL1":4,"COL2":"PFF"}}
{"_index":"test01","_type":"_doc","_id":"Z","_score":1,"_source":{"COL1":1,"COL2":"WOO"}}
```
:::
::::

::: paragraph
Now send a tombstone message by writing a NULL value to the underlying
topic:
:::

:::: listingblock
::: content
``` highlight
CREATE STREAM TEST01_TOMBSTONE (ALPHA VARCHAR KEY,COL1 VARCHAR)
  WITH (KAFKA_TOPIC='test01', VALUE_FORMAT='KAFKA', KEY_FORMAT='AVRO');

INSERT INTO TEST01_TOMBSTONE (ALPHA, COL1) VALUES ('Y',CAST(NULL AS VARCHAR));
```
:::
::::

::: paragraph
Check the topic:
:::

:::: listingblock
::: content
``` highlight
PRINT test01 FROM BEGINNING;
```
:::
::::

:::: listingblock
::: content
``` highlight
rowtime: 4/30/20 4:24:12 PM UTC, key: X, value: {"COL1": 1, "COL2": "FOO"}
rowtime: 4/30/20 4:24:12 PM UTC, key: Y, value: {"COL1": 2, "COL2": "BAR"}
rowtime: 4/30/20 4:24:19 PM UTC, key: Z, value: {"COL1": 1, "COL2": "WOO"}
rowtime: 4/30/20 4:24:19 PM UTC, key: Y, value: {"COL1": 4, "COL2": "PFF"}
rowtime: 4/30/20 4:27:50 PM UTC, key: Y, value: <null>
```
:::
::::

::: paragraph
Check Elasticsearch to see that document with key `Y` has been deleted:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test01/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test01","_type":"_doc","_id":"X","_score":1,"_source":{"COL1":1,"COL2":"FOO"}}
{"_index":"test01","_type":"_doc","_id":"Z","_score":1,"_source":{"COL1":1,"COL2":"WOO"}}
```
:::
::::
:::::::::::::::::::::::::::::::::
:::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sect1
## Schemas (& general troubleshooting) {#_schemas_general_troubleshooting}

::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sectionbody
::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=974s)
:::

::: ulist
-   `schemas.ignore=false` means that Kafka Connect will define the
    index mapping based on the schema of the source data

    ::: ulist
    -   If you use this it is **mandatory** to have a source schema
        (e.g. Avro, Protobuf, JSON Schema etc --- *NOT* plain JSON)
    :::

-   `schemas.ignore=true` means Kafka Connect will just send the values
    and let Elasticsearch figure out how to map them using [dynamic
    field
    mapping](https://www.elastic.co/guide/en/elasticsearch/reference/current/dynamic-field-mapping.html)
    and optionally [dynamic
    templates](https://www.elastic.co/guide/en/elasticsearch/reference/current/dynamic-templates.html)
    that you define in advance.
:::

::: paragraph
Set up some JSON data in a topic:
:::

:::: listingblock
::: content
``` highlight
CREATE STREAM TEST_JSON (COL1 INT, COL2 VARCHAR) WITH (KAFKA_TOPIC='TEST_JSON', PARTITIONS=1, VALUE_FORMAT='JSON');
INSERT INTO TEST_JSON (COL1, COL2) VALUES (1,'FOO');
INSERT INTO TEST_JSON (COL1, COL2) VALUES (2,'BAR');
```
:::
::::

:::::::::::::::: sect2
### Error 1 (reading JSON data with Avro converter) {#_error_1_reading_json_data_with_avro_converter}

::: paragraph
Try streaming this JSON data to to Elasticsearch
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_JSON_A WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'type.name'               = '_doc',
  'topics'                  = 'TEST_JSON',
  'key.ignore'              = 'true',
  'schema.ignore'           = 'false'
);
```
:::
::::

::: paragraph
Connector fails. Why?
:::

:::: listingblock
::: content
``` highlight
DESCRIBE CONNECTOR SINK_ELASTIC_TEST_JSON_A;

Name                 : SINK_ELASTIC_TEST_JSON_A
Class                : io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
Type                 : sink
State                : RUNNING
WorkerId             : kafka-connect:8083

 Task ID | State  | Error Trace
----------------------------------------------------------------------------------------------------------------------------------
 0       | FAILED | org.apache.kafka.connect.errors.ConnectException: Tolerance exceeded in error handler
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndHandleError(RetryWithToleranceOperator.java:206)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execute(RetryWithToleranceOperator.java:132)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertAndTransformRecord(WorkerSinkTask.java:501)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertMessages(WorkerSinkTask.java:478)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.poll(WorkerSinkTask.java:328)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.iteration(WorkerSinkTask.java:232)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.execute(WorkerSinkTask.java:201)
        at org.apache.kafka.connect.runtime.WorkerTask.doRun(WorkerTask.java:185)
        at org.apache.kafka.connect.runtime.WorkerTask.run(WorkerTask.java:234)
        at java.base/java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:515)
        at java.base/java.util.concurrent.FutureTask.run(FutureTask.java:264)
        at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1128)
        at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:628)
        at java.base/java.lang.Thread.run(Thread.java:834)
Caused by: org.apache.kafka.connect.errors.DataException: Failed to deserialize data for topic TEST_JSON to Avro:
        at io.confluent.connect.avro.AvroConverter.toConnectData(AvroConverter.java:125)
        at org.apache.kafka.connect.storage.Converter.toConnectData(Converter.java:87)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertValue(WorkerSinkTask.java:545)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.lambda$convertAndTransformRecord$1(WorkerSinkTask.java:501)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndRetry(RetryWithToleranceOperator.java:156)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndHandleError(RetryWithToleranceOperator.java:190)
        ... 13 more
Caused by: org.apache.kafka.common.errors.SerializationException: Unknown magic byte!

----------------------------------------------------------------------------------------------------------------------------------
```
:::
::::

::: paragraph
Error within this is:
:::

:::: listingblock
::: content
``` highlight
org.apache.kafka.connect.errors.DataException: Failed to deserialize data for topic TEST_JSON to Avro:
…
Caused by: org.apache.kafka.common.errors.SerializationException: Unknown magic byte!
```
:::
::::

::: paragraph
We're reading JSON data but using the Avro converter (as specified as
the default converter for the worker) in the Docker Compose:
:::

:::: listingblock
::: content
``` highlight
  kafka-connect:
    image: confluentinc/cp-kafka-connect-base:6.1.0
…
    environment:
      CONNECT_VALUE_CONVERTER: io.confluent.connect.avro.AvroConverter
      CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL: 'http://schema-registry:8081'
```
:::
::::

::: paragraph
Ref:
[https://www.confluent.io/blog/kafka-connect-deep-dive-converters-serialization-explained/](https://www.confluent.io/blog/kafka-connect-deep-dive-converters-serialization-explained/){.bare}
:::
::::::::::::::::

:::::::::::::: sect2
### Error 2 (reading JSON data and expecting a schema) {#_error_2_reading_json_data_and_expecting_a_schema}

::: paragraph
So recreate the connector and specify JSON converter (because we're
reading JSON data from the topic)
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_JSON_A;
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_JSON_A WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'         = 'org.apache.kafka.connect.json.JsonConverter',
  'value.converter.schemas.enable' = 'true',
  'type.name'               = '_doc',
  'topics'                  = 'TEST_JSON',
  'key.ignore'              = 'true',
  'schema.ignore'           = 'false'
);
```
:::
::::

::: paragraph
Fails
:::

:::: listingblock
::: content
``` highlight
DESCRIBE CONNECTOR SINK_ELASTIC_TEST_JSON_A;

Name                 : SINK_ELASTIC_TEST_JSON_A
Class                : io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
Type                 : sink
State                : RUNNING
WorkerId             : kafka-connect:8083

 Task ID | State  | Error Trace
----------------------------------------------------------------------------------------------------------------------------------
 0       | FAILED | org.apache.kafka.connect.errors.ConnectException: Tolerance exceeded in error handler
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndHandleError(RetryWithToleranceOperator.java:206)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execute(RetryWithToleranceOperator.java:132)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertAndTransformRecord(WorkerSinkTask.java:501)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertMessages(WorkerSinkTask.java:478)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.poll(WorkerSinkTask.java:328)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.iteration(WorkerSinkTask.java:232)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.execute(WorkerSinkTask.java:201)
        at org.apache.kafka.connect.runtime.WorkerTask.doRun(WorkerTask.java:185)
        at org.apache.kafka.connect.runtime.WorkerTask.run(WorkerTask.java:234)
        at java.base/java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:515)
        at java.base/java.util.concurrent.FutureTask.run(FutureTask.java:264)
        at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1128)
        at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:628)
        at java.base/java.lang.Thread.run(Thread.java:834)
Caused by: org.apache.kafka.connect.errors.DataException: JsonConverter with schemas.enable requires "schema" and "payload" fields and may not contain additional fields. If you are trying to deserialize plain JSON data, set schemas.enable=false in your converter configuration.
        at org.apache.kafka.connect.json.JsonConverter.toConnectData(JsonConverter.java:370)
        at org.apache.kafka.connect.storage.Converter.toConnectData(Converter.java:87)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.convertValue(WorkerSinkTask.java:545)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.lambda$convertAndTransformRecord$1(WorkerSinkTask.java:501)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndRetry(RetryWithToleranceOperator.java:156)
        at org.apache.kafka.connect.runtime.errors.RetryWithToleranceOperator.execAndHandleError(RetryWithToleranceOperator.java:190)
        ... 13 more

----------------------------------------------------------------------------------------------------------------------------------
```
:::
::::

::: paragraph
Nested error:
:::

:::: listingblock
::: content
``` highlight
org.apache.kafka.connect.errors.DataException: JsonConverter with schemas.enable requires \"schema\" and \"payload\" fields and may not contain additional fields. If you are trying to deserialize plain JSON data, set schemas.enable=false in your converter configuration.
```
:::
::::

::: paragraph
We're reading JSON data but have told the converter to look for a schema
(`schemas.enable`) which we don't have.
:::

::: paragraph
Ref:
[https://www.confluent.io/blog/kafka-connect-deep-dive-converters-serialization-explained/](https://www.confluent.io/blog/kafka-connect-deep-dive-converters-serialization-explained/){.bare}
:::
::::::::::::::

:::::::::::::::: sect2
### Error 3 (Connector requires a schema but there isn't one) {#_error_3_connector_requires_a_schema_but_there_isnt_one}

::: paragraph
Recreate the connector and set the converter to not expect a schema
embedded in the JSON data (`value.converter.schemas.enable' = 'false'`):
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_JSON_A;
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_JSON_A WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'         = 'org.apache.kafka.connect.json.JsonConverter',
  'value.converter.schemas.enable' = 'false',
  'type.name'               = '_doc',
  'topics'                  = 'TEST_JSON',
  'key.ignore'              = 'true',
  'schema.ignore'           = 'false'
);
```
:::
::::

::: paragraph
Connector fails
:::

:::: listingblock
::: content
``` highlight
ksql> DESCRIBE CONNECTOR SINK_ELASTIC_TEST_JSON_A;

Name                 : SINK_ELASTIC_TEST_JSON_A
Class                : io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
Type                 : sink
State                : RUNNING
WorkerId             : kafka-connect:8083

 Task ID | State  | Error Trace
------------------------------------------------------------------------------------------------------------------------------
 0       | FAILED | org.apache.kafka.connect.errors.ConnectException: Exiting WorkerSinkTask due to unrecoverable exception.
        at org.apache.kafka.connect.runtime.WorkerSinkTask.deliverMessages(WorkerSinkTask.java:614)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.poll(WorkerSinkTask.java:329)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.iteration(WorkerSinkTask.java:232)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.execute(WorkerSinkTask.java:201)
        at org.apache.kafka.connect.runtime.WorkerTask.doRun(WorkerTask.java:185)
        at org.apache.kafka.connect.runtime.WorkerTask.run(WorkerTask.java:234)
        at java.base/java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:515)
        at java.base/java.util.concurrent.FutureTask.run(FutureTask.java:264)
        at java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1128)
        at java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:628)
        at java.base/java.lang.Thread.run(Thread.java:834)
Caused by: org.apache.kafka.connect.errors.DataException: Cannot infer mapping without schema.
        at io.confluent.connect.elasticsearch.Mapping.buildMapping(Mapping.java:81)
        at io.confluent.connect.elasticsearch.Mapping.buildMapping(Mapping.java:68)
        at io.confluent.connect.elasticsearch.ElasticsearchClient.createMapping(ElasticsearchClient.java:212)
        at io.confluent.connect.elasticsearch.ElasticsearchSinkTask.checkMapping(ElasticsearchSinkTask.java:121)
        at io.confluent.connect.elasticsearch.ElasticsearchSinkTask.put(ElasticsearchSinkTask.java:91)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.deliverMessages(WorkerSinkTask.java:586)
        ... 10 more

------------------------------------------------------------------------------------------------------------------------------
```
:::
::::

::: paragraph
Nested error:
:::

:::: listingblock
::: content
``` highlight
org.apache.kafka.connect.errors.DataException: Cannot infer mapping without schema.
```
:::
::::

::: paragraph
The connector is being told that we **will** supply a schema with the
data that will be used to create the Elasticsearch mapping:
:::

:::: listingblock
::: content
``` highlight
'schema.ignore'           = 'false'
```
:::
::::

::: paragraph
**BUT** we do not have a declared schema in the data.
:::
::::::::::::::::

::::::::::: sect2
### Success! {#_success}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=1557s)
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_JSON_A;
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_JSON_A WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'         = 'org.apache.kafka.connect.json.JsonConverter',
  'value.converter.schemas.enable' = 'false',
  'type.name'               = '_doc',
  'topics'                  = 'TEST_JSON',
  'key.ignore'              = 'true',
  'schema.ignore'           = 'true'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
ksql> DESCRIBE CONNECTOR SINK_ELASTIC_TEST_JSON_A;

Name                 : SINK_ELASTIC_TEST_JSON_A
Class                : io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
Type                 : sink
State                : RUNNING
WorkerId             : kafka-connect:8083

 Task ID | State   | Error Trace
---------------------------------
 0       | RUNNING |
---------------------------------
```
:::
::::

::: paragraph
Data is in Elasticsearch:
:::

:::: listingblock
::: content
``` highlight
➜ curl -s http://localhost:9200/test_json/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
{"_index":"test_json","_type":"_doc","_id":"TEST_JSON+0+0","_score":1,"_source":{"COL2":"FOO","COL1":1}}
{"_index":"test_json","_type":"_doc","_id":"TEST_JSON+0+1","_score":1,"_source":{"COL2":"BAR","COL1":2}}
```
:::
::::
:::::::::::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sect1
## Timestamps {#_timestamps}

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sectionbody
::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=1737s)
:::

:::: listingblock
::: content
``` highlight
CREATE STREAM TEST02 (COL0 VARCHAR KEY, COL1 INT, ORDER_TS_EPOCH BIGINT, SHIP_TS_STR VARCHAR)
  WITH (KAFKA_TOPIC='test02', PARTITIONS=1, VALUE_FORMAT='AVRO');

INSERT INTO TEST02 (COL0, COL1, ORDER_TS_EPOCH, SHIP_TS_STR)
  VALUES ('MY_KEY__X',
          1,
          STRINGTOTIMESTAMP('2020-02-17T15:22:00Z','yyyy-MM-dd''T''HH:mm:ssX'),
          '2020-02-17T15:22:00Z');

INSERT INTO TEST02 (COL0, COL1, ORDER_TS_EPOCH, SHIP_TS_STR)
  VALUES ('MY_KEY__Y',
          1,
          STRINGTOTIMESTAMP('2020-02-17T15:26:00Z','yyyy-MM-dd''T''HH:mm:ssX'),
          '2020-02-17T15:26:00Z');
```
:::
::::

:::: listingblock
::: content
``` highlight
PRINT test02 FROM BEGINNING;
```
:::
::::

:::: listingblock
::: content
``` highlight
Key format: HOPPING(KAFKA_STRING) or TUMBLING(KAFKA_STRING) or KAFKA_STRING
Value format: AVRO
rowtime: 5/4/20 10:24:46 AM UTC, key: [M@6439948753387347800/-], value: {"COL1": 1, "ORDER_TS_EPOCH": 1581952920000, "SHIP_TS_STR": "2020-02-17T15:22:00Z"}
rowtime: 5/4/20 10:24:47 AM UTC, key: [M@6439948753387347801/-], value: {"COL1": 1, "ORDER_TS_EPOCH": 1581953160000, "SHIP_TS_STR": "2020-02-17T15:26:00Z"}
```
:::
::::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_A WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'= 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url'= 'http://schema-registry:8081',
  'type.name'               = '_doc',
  'topics'                  = 'test02',
  'key.ignore'              = 'false',
  'schema.ignore'           = 'false'
);
```
:::
::::

::: paragraph
Check we've got data:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test02","_type":"_doc","_id":"MY_KEY__Y","_score":1,"_source":{"COL1":1,"ORDER_TS_EPOCH":1581953160000,"SHIP_TS_STR":"2020-02-17T15:26:00Z"}}
{"_index":"test02","_type":"_doc","_id":"MY_KEY__X","_score":1,"_source":{"COL1":1,"ORDER_TS_EPOCH":1581952920000,"SHIP_TS_STR":"2020-02-17T15:22:00Z"}}
```
:::
::::

::: paragraph
Check the mappings - note neither of the timestamps are `date` types
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "properties": {
        "COL1": {
          "type": "integer"
        },
        "ORDER_TS_EPOCH": {
          "type": "long"
        },
        "SHIP_TS_STR": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
Drop the connector
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_02_A;
```
:::
::::

::: paragraph
Drop the index
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test02"
```
:::
::::

:::::::::::::::::: sect2
### Let Elasticsearch guess at the data types (dynamic field mapping) {#_let_elasticsearch_guess_at_the_data_types_dynamic_field_mapping}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=1994s)
:::

::: paragraph
Ref: [dynamic
mapping](https://www.elastic.co/guide/en/elasticsearch/reference/current/dynamic-field-mapping.html)
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_B WITH (
  'connector.class'         = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'          = 'http://elasticsearch:9200',
  'key.converter'           = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'= 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url'= 'http://schema-registry:8081',
  'type.name'               = '_doc',
  'topics'                  = 'test02',
  'key.ignore'              = 'false',
  'schema.ignore'           = 'true'
);
```
:::
::::

::: paragraph
Picks up string (`SHIP_TS_STR`) because it looks like one, but not the
epoch (`ORDER_TS_EPOCH`)
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "properties": {
        "COL1": {
          "type": "long"
        },
        "ORDER_TS_EPOCH": {
          "type": "long"
        },
        "SHIP_TS_STR": {
          "type": "date"
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
Drop the connector
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_02_B;
```
:::
::::

::: paragraph
Drop the index
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test02"
```
:::
::::
::::::::::::::::::

::::::::::::::::: sect2
### Specify field as a Timestamp using a Single Message Transform {#_specify_field_as_a_timestamp_using_a_single_message_transform}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=2181s)
:::

::: paragraph
Ref:
[https://docs.confluent.io/current/connect/transforms/timestampconverter.html](https://docs.confluent.io/current/connect/transforms/timestampconverter.html){.bare}
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_C WITH (
  'connector.class'                          = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'                           = 'http://elasticsearch:9200',
  'key.converter'                            = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'                          = 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url'      = 'http://schema-registry:8081',
  'type.name'                                = '_doc',
  'topics'                                   = 'test02',
  'key.ignore'                               = 'false',
  'schema.ignore'                            = 'false',
  'transforms'                               = 'setTimestampType0',
  'transforms.setTimestampType0.type'        = 'org.apache.kafka.connect.transforms.TimestampConverter$Value',
  'transforms.setTimestampType0.field'       = 'ORDER_TS_EPOCH',
  'transforms.setTimestampType0.target.type' = 'Timestamp'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "properties": {
        "COL1": {
          "type": "integer"
        },
        "ORDER_TS_EPOCH": {
          "type": "date"
        },
        "SHIP_TS_STR": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
Drop the connector
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_02_C;
```
:::
::::

::: paragraph
Drop the index
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test02"
```
:::
::::
:::::::::::::::::

:::::::::::::::::::::::: sect2
### Declare the timestamp type in Elasticsearch in advance with Dynamic Template {#_declare_the_timestamp_type_in_elasticsearch_in_advance_with_dynamic_template}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=2329s)
:::

::: paragraph
Create dynamic template
:::

:::: listingblock
::: content
``` highlight
curl -s -XPUT "http://localhost:9200/_template/rmoff/" -H 'Content-Type: application/json' -d'
          {
            "template": "*",
            "mappings": { "dynamic_templates": [ { "dates": { "match": "*_TS_*", "mapping": { "type": "date" } } } ]  }
          }'
```
:::
::::

::: paragraph
Create the connector
:::

::: {.admonitionblock .note}
+-----------------------------------+-----------------------------------+
| ::: title                         | `schema.ignore` is set to `true`, |
| Note                              | since we want Elasticsearch to    |
| :::                               | use its dynamic field mapping and |
|                                   | thus dynamic templates to         |
|                                   | determine the mapping types.      |
+-----------------------------------+-----------------------------------+
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_D WITH (
  'connector.class'                     = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'                      = 'http://elasticsearch:9200',
  'key.converter'                       = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'                     = 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url' = 'http://schema-registry:8081',
  'type.name'                           = '_doc',
  'topics'                              = 'test02',
  'key.ignore'                          = 'false',
  'schema.ignore'                       = 'true'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "dynamic_templates": [
        {
          "dates": {
            "match": "*_TS_*",
            "mapping": {
              "type": "date"
            }
          }
        }
      ],
      "properties": {
        "COL1": {
          "type": "long"
        },
        "ORDER_TS_EPOCH": {
          "type": "date"
        },
        "SHIP_TS_STR": {
          "type": "date"
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
Drop connector :
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_02_D;
```
:::
::::

::: paragraph
Drop index
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test02"
```
:::
::::

::: paragraph
Drop dynamic template
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/_template/rmoff/"
```
:::
::::
::::::::::::::::::::::::

::::::::::::::::::::::::::::::: sect2
### Add Kafka message timestamp as Elasticsearch timestamp field {#_add_kafka_message_timestamp_as_elasticsearch_timestamp_field}

::: paragraph
What about if we want to use the Kafka message's timestamp? Producer can
set this, no point duplicating it in the message value itself.
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_E WITH (
  'connector.class'                             = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'                              = 'http://elasticsearch:9200',
  'key.converter'                               = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'                             = 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url'         = 'http://schema-registry:8081',
  'type.name'                                   = '_doc',
  'topics'                                      = 'test02',
  'key.ignore'                                  = 'false',
  'schema.ignore'                               = 'false',
  'transforms'                                  = 'ExtractTimestamp',
  'transforms.ExtractTimestamp.type'            = 'org.apache.kafka.connect.transforms.InsertField$Value',
  'transforms.ExtractTimestamp.timestamp.field' = 'MSG_TS'
);
```
:::
::::

::: paragraph
Elasticsearch data:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test02","_type":"_doc","_id":"MY_KEY__X","_score":1,"_source":{"COL1":1,"ORDER_TS_EPOCH":1581952920000,"SHIP_TS_STR":"2020-02-17T15:22:00Z","MSG_TS":1588587886954}}
{"_index":"test02","_type":"_doc","_id":"MY_KEY__Y","_score":1,"_source":{"COL1":1,"ORDER_TS_EPOCH":1581953160000,"SHIP_TS_STR":"2020-02-17T15:26:00Z","MSG_TS":1588587887036}}
```
:::
::::

::: paragraph
Mapping for `MSG_TS` is `date` but since dynamic mapping is in use and
there's no dynamic template the other two date fields are not seen as
`date`:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "properties": {
        "COL1": {
          "type": "integer"
        },
        "MSG_TS": {
          "type": "date"
        },
        "ORDER_TS_EPOCH": {
          "type": "long"
        },
        "SHIP_TS_STR": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
Alternatives include:
:::

::: {.olist .arabic}
1.  `schema.ignore=false` and SMT to set timestamp types
    (\`org.apache.kafka.connect.transforms.TimestampConverter)

2.  `schema.ignore=true` and use a dynamic template

3.  `schema.ignore=true` and SMT to force `MSG_TS` to string so that
    Elasticsearch can guess at it correctly - see below
:::

::: paragraph
Drop connector
:::

:::: listingblock
::: content
``` highlight
DROP CONNECTOR SINK_ELASTIC_TEST_02_E;
```
:::
::::

::: paragraph
Drop index
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s -XDELETE "http://localhost:9200/test02"
```
:::
::::

::: paragraph
Create connector
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_02_F WITH (
  'connector.class'                             = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'                              = 'http://elasticsearch:9200',
  'key.converter'                               = 'org.apache.kafka.connect.storage.StringConverter',
  'value.converter'                             = 'io.confluent.connect.avro.AvroConverter',
  'value.converter.schema.registry.url'         = 'http://schema-registry:8081',
  'type.name'                                   = '_doc',
  'topics'                                      = 'test02',
  'key.ignore'                                  = 'false',
  'schema.ignore'                               = 'true',
  'transforms'                                  = 'ExtractTimestamp, setTimestampType',
  'transforms.ExtractTimestamp.type'            = 'org.apache.kafka.connect.transforms.InsertField$Value',
  'transforms.ExtractTimestamp.timestamp.field' = 'MSG_TS',
  'transforms.setTimestampType.type'            = 'org.apache.kafka.connect.transforms.TimestampConverter$Value',
  'transforms.setTimestampType.field'           = 'MSG_TS',
  'transforms.setTimestampType.target.type'     = 'string',
  'transforms.setTimestampType.format'          = 'yyyy-MM-dd\''T\''HH:mm:ssX'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test02/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test02": {
    "mappings": {
      "properties": {
        "COL1": {
          "type": "long"
        },
        "MSG_TS": {
          "type": "date"
        },
        "ORDER_TS_EPOCH": {
          "type": "long"
        },
        "SHIP_TS_STR": {
          "type": "date"
        }
      }
    }
  }
}
```
:::
::::
:::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:::::::::::::::::::::::::::::::::::::: sect1
## Index naming and partitioning {#_index_naming_and_partitioning}

::::::::::::::::::::::::::::::::::::: sectionbody
::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=2840s)
:::

::: paragraph
Index name by default is the topic name, forced to lowercase
automagically if necessary:
:::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s "http://localhost:9200/_cat/indices/*?h=idx,docsCount" |grep -v '^\.'
```
:::
::::

:::: listingblock
::: content
``` highlight
test02                   2
```
:::
::::

:::::::::::: sect2
### Change target index name with RegEx {#_change_target_index_name_with_regex}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=2881s)
:::

::: paragraph
Ref:
[https://docs.confluent.io/current/connect/transforms/regexrouter.html](https://docs.confluent.io/current/connect/transforms/regexrouter.html){.bare}
:::

::: paragraph
See also
[https://rmoff.net/2020/12/11/twelve-days-of-smt-day-4-regexrouter/](https://rmoff.net/2020/12/11/twelve-days-of-smt-day-4-regexrouter/){.bare}
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_04 WITH (
  'connector.class' = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'  = 'http://elasticsearch:9200',
  'key.converter'   = 'org.apache.kafka.connect.storage.StringConverter',
  'type.name'       = '_doc',
  'topics'          = 'test02',
  'key.ignore'      = 'true',
  'schema.ignore'   = 'true',
  'transforms'      = 'changeIndexname',
  'transforms.changeIndexname.type'        = 'org.apache.kafka.connect.transforms.RegexRouter',
  'transforms.changeIndexname.regex'       = '(.*)02',
  'transforms.changeIndexname.replacement' = 'foo-$1'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s "http://localhost:9200/_cat/indices/*?h=idx,docsCount" |grep -v '^\.'
```
:::
::::

:::: listingblock
::: content
``` highlight
test02                   2
foo-test                 2
```
:::
::::
::::::::::::

:::::::::::: sect2
### Use date / time in the target index name {#_use_date_time_in_the_target_index_name}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=2975s)
:::

::: paragraph
Ref:
[https://docs.confluent.io/current/connect/transforms/timestamprouter.html](https://docs.confluent.io/current/connect/transforms/timestamprouter.html){.bare}
:::

::: paragraph
See also
[https://rmoff.net/2020/12/16/twelve-days-of-smt-day-7-timestamprouter/](https://rmoff.net/2020/12/16/twelve-days-of-smt-day-7-timestamprouter/){.bare}
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_05 WITH (
  'connector.class' = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'  = 'http://elasticsearch:9200',
  'key.converter'   = 'org.apache.kafka.connect.storage.StringConverter',
  'type.name'       = '_doc',
  'topics'          = 'test02',
  'key.ignore'      = 'true',
  'schema.ignore'   = 'true',
  'transforms'      = 'appendTimestampToIX',
  'transforms.appendTimestampToIX.type'        = 'org.apache.kafka.connect.transforms.TimestampRouter',
  'transforms.appendTimestampToIX.topic.format' = '${topic}-${timestamp}',
  'transforms.appendTimestampToIX.timestamp.format' = 'yyyy-MM-dd'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s "http://localhost:9200/_cat/indices/*?h=idx,docsCount" |grep -v '^\.'
```
:::
::::

:::: listingblock
::: content
``` highlight
test02                   2
test02-2020-05-01        2
foo-test                 2
```
:::
::::
::::::::::::

:::::::::: sect2
### Use both regex and date/time in target index name {#_use_both_regex_and_datetime_in_target_index_name}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=3117s)
:::

:::: listingblock
::: content
``` highlight
CREATE SINK CONNECTOR SINK_ELASTIC_TEST_06 WITH (
  'connector.class' = 'io.confluent.connect.elasticsearch.ElasticsearchSinkConnector',
  'connection.url'  = 'http://elasticsearch:9200',
  'key.converter'   = 'org.apache.kafka.connect.storage.StringConverter',
  'type.name'       = '_doc',
  'topics'          = 'test02',
  'key.ignore'      = 'true',
  'schema.ignore'   = 'true',
  'transforms'      = 'changeIndexname,appendTimestampToIX',
  'transforms.changeIndexname.type'        = 'org.apache.kafka.connect.transforms.RegexRouter',
  'transforms.changeIndexname.regex'       = '(.*)02',
  'transforms.changeIndexname.replacement' = 'foo-$1',
  'transforms.appendTimestampToIX.type'        = 'org.apache.kafka.connect.transforms.TimestampRouter',
  'transforms.appendTimestampToIX.topic.format' = '${topic}-${timestamp}',
  'transforms.appendTimestampToIX.timestamp.format' = 'yyyy-MM-dd'
);
```
:::
::::

:::: listingblock
::: content
``` highlight
docker exec elasticsearch curl -s "http://localhost:9200/_cat/indices/*?h=idx,docsCount" |grep -v '^\.'
```
:::
::::

:::: listingblock
::: content
``` highlight
test02                   2
test02-2020-05-01        2
foo-test                 2
foo-test-2020-05-01      2
```
:::
::::
::::::::::
:::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sect1
## Error Handling in Kafka Connect and Elasticsearch Sink connector {#_error_handling_in_kafka_connect_and_elasticsearch_sink_connector}

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: sectionbody
::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=3180s)
:::

::: paragraph
Ref:
[https://www.confluent.io/blog/kafka-connect-deep-dive-error-handling-dead-letter-queues/](https://www.confluent.io/blog/kafka-connect-deep-dive-error-handling-dead-letter-queues/){.bare}
:::

::: {.admonitionblock .note}
+-----------------------------------+-----------------------------------+
| ::: title                         | This section also illustrates     |
| Note                              | working with Kafka Connect using  |
| :::                               | the REST API directly instead of  |
|                                   | the ksqlDB interface as shown     |
|                                   | above.                            |
+-----------------------------------+-----------------------------------+
:::

::: paragraph
Write to a topic:
:::

::: paragraph
echo \'1:{\"a\":1}\' \| \\ docker exec -i kafkacat kafkacat \\ -b
broker:29092 \\ -P -t test03 -Z -K:
:::

::: paragraph
For info you can read from the topic if you want to:
:::

:::: listingblock
::: content
``` highlight
docker exec kafkacat kafkacat \
        -b broker:29092 \
        -C -o beginning -u -q \
        -t test03 \
        -f 'Topic+Partition+Offset: %t+%p+%o\tKey: %k\tValue: %s\n'
```
:::
::::

::: paragraph
Create the connector:
:::

:::: listingblock
::: content
``` highlight
curl -i -X PUT -H  "Content-Type:application/json" \
  http://localhost:8083/connectors/sink-elastic-test03/config \
  -d '{
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "key.converter"                   : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                 : "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable"  : "false",
    "topics"                          : "test03",
    "connection.url"                  : "http://elasticsearch:9200",
    "type.name"                       : "_doc",
    "key.ignore"                      : "false",
    "schema.ignore"                   : "true"
}'
```
:::
::::

::: paragraph
Works as designed
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test03/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test03","_type":"_doc","_id":"1","_score":1,"_source":{"a":1}}
```
:::
::::

::: paragraph
Now send a bad message (malformed JSON)
:::

:::: listingblock
::: content
``` highlight
echo '1:{"fieldnamewithoutclosingquote:1}' | \
  docker exec -i kafkacat kafkacat \
          -b broker:29092 \
          -P -t test03 -Z -K:
```
:::
::::

::: paragraph
Check connector status
:::

:::: listingblock
::: content
``` highlight
curl -s "http://localhost:8083/connectors?expand=info&expand=status" | \
       jq '. | to_entries[] | [ .value.info.type, .key, .value.status.connector.state,.value.status.tasks[].state,.value.info.config."connector.class"]|join(":|:")' | \
       column -s : -t| sed 's/\"//g'| sort
```
:::
::::

:::: listingblock
::: content
``` highlight
sink  |  sink-elastic-test03   |  RUNNING  |  FAILED   |  io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
```
:::
::::

::: paragraph
Check error
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:8083/connectors/sink-elastic-test03/status | jq -r '.tasks[].trace'
```
:::
::::

:::: listingblock
::: content
``` highlight
org.apache.kafka.connect.errors.DataException: Converting byte[] to Kafka Connect data failed due to serialization error:
…
org.apache.kafka.common.errors.SerializationException: com.fasterxml.jackson.core.io.JsonEOFException: Unexpected end-of-input in field name
 at [Source: (byte[])"{"fieldnamewithoutclosingquote:1}"; line: 1, column: 34]
```
:::
::::

:::::::::::::::::::::::::: sect2
### Ignore messages that cannot be deserialised {#_ignore_messages_that_cannot_be_deserialised}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=3433s)
:::

::: paragraph
Add error handling
:::

:::: listingblock
::: content
``` highlight
"errors.tolerance"                : "all",
"errors.log.enable"               : "true"
"errors.log.include.messages"     : "true"
```
:::
::::

::: paragraph
*This uses a `PUT` which creates the config if not there, and updates it
if it is. Much easier than delete/create each time.*
:::

:::: listingblock
::: content
``` highlight
curl -i -X PUT -H  "Content-Type:application/json" \
  http://localhost:8083/connectors/sink-elastic-test03/config \
  -d '{
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "key.converter"                   : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                 : "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable"  : "false",
    "topics"                          : "test03",
    "connection.url"                  : "http://elasticsearch:9200",
    "type.name"                       : "_doc",
    "key.ignore"                      : "false",
    "schema.ignore"                   : "true",
    "errors.tolerance"                : "all",
    "errors.log.enable"               : "true",
    "errors.log.include.messages"     : "true"
}'
```
:::
::::

::: paragraph
Connector runs:
:::

:::: listingblock
::: content
``` highlight
curl -s "http://localhost:8083/connectors?expand=info&expand=status" | \
       jq '. | to_entries[] | [ .value.info.type, .key, .value.status.connector.state,.value.status.tasks[].state,.value.info.config."connector.class"]|join(":|:")' | \
       column -s : -t| sed 's/\"//g'| sort
```
:::
::::

:::: listingblock
::: content
``` highlight
sink  |  sink-elastic-test03  |  RUNNING  |  RUNNING  |  io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
```
:::
::::

::: paragraph
Logs an message for the malformed message:
:::

:::: listingblock
::: content
``` highlight
docker logs kafka-connect
```
:::
::::

::: paragraph
Validate that the pipeline is running by sending a good message
:::

:::: listingblock
::: content
``` highlight
echo '3:{"a":3}' | \
  docker exec -i kafkacat kafkacat \
          -b broker:29092 \
          -P -t test03 -Z -K:
```
:::
::::

::: paragraph
Verify it's present in Elasticsearch:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test03/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test03","_type":"_doc","_id":"1","_score":1,"_source":{"a":1}}
{"_index":"test03","_type":"_doc","_id":"3","_score":1,"_source":{"a":3}}
```
:::
::::
::::::::::::::::::::::::::

::::::::::::::: sect2
### Setting up a dead letter queue for Elasticsearch sink {#_setting_up_a_dead_letter_queue_for_elasticsearch_sink}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=3571s)
:::

:::: listingblock
::: content
``` highlight
curl -i -X PUT -H  "Content-Type:application/json" \
  http://localhost:8083/connectors/sink-elastic-test03/config \
  -d '{
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "key.converter"                   : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                 : "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable"  : "false",
    "topics"                          : "test03",
    "connection.url"                  : "http://elasticsearch:9200",
    "type.name"                       : "_doc",
    "key.ignore"                      : "false",
    "schema.ignore"                   : "true",
    "errors.tolerance"                : "all",
    "errors.log.enable"               : "true",
    "errors.log.include.messages"     : "true",
    "errors.deadletterqueue.topic.name":"dlq_sink-elastic-test03",
    "errors.deadletterqueue.topic.replication.factor": 1,
    "errors.deadletterqueue.context.headers.enable":true
}'
```
:::
::::

::: paragraph
Send a badly-formed message
:::

:::: listingblock
::: content
``` highlight
echo '4:{never gonna give you up}' | \
  docker exec -i kafkacat kafkacat \
          -b broker:29092 \
          -P -t test03 -Z -K:
```
:::
::::

::: paragraph
Look at the dead letter queue topic:
:::

:::: listingblock
::: content
``` highlight
docker exec kafkacat kafkacat \
        -b broker:29092 \
        -C -o beginning -u -q \
        -t dlq_sink-elastic-test03 \
        -f '%t\tKey: %k\tValue: %s\nHeaders: %h\n'
```
:::
::::

:::: listingblock
::: content
``` highlight
dlq_sink-elastic-test03 Key: 4  Value: {never gonna give you up}
Headers: __connect.errors.topic=test03,__connect.errors.partition=0,__connect.errors.offset=3,__connect.errors.connector.name=sink-elastic-te
st03,__connect.errors.task.id=0,__connect.errors.stage=VALUE_CONVERTER,__connect.errors.class.name=org.apache.kafka.connect.json.JsonConverte
r,__connect.errors.exception.class.name=org.apache.kafka.connect.errors.DataException,__connect.errors.exception.message=Converting byte[] to
 Kafka Connect data failed due to serialization error: ,__connect.errors.exception.stacktrace=org.apache.kafka.connect.errors.DataException:
Converting byte[] to Kafka Connect data failed due to serialization error:
…
Caused by: org.apache.kafka.common.errors.SerializationException: com.fasterxml.jackson.core.JsonParseException: Unexpected character ('n' (c
ode 110)): was expecting double-quote to start field name
 at [Source: (byte[])"{never gonna give you up}"; line: 1, column: 3]
```
:::
::::

::: paragraph
Note how the full stack trace for the error is available from the header
of the Kafka message, along with details of its source message offset
etc
:::
:::::::::::::::

:::::::::::::::::::::::::::::::::::::: sect2
### Dealing with correctly-formed messages that are invalid for Elasticsearch {#_dealing_with_correctly_formed_messages_that_are_invalid_for_elasticsearch}

::: paragraph
[🎥 Watch](https://www.youtube.com/watch?v=Cq-2eGxOCc8&t=3743s)
:::

::: paragraph
Target mapping has field `a` with type `long`:
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test03/_mapping | jq '.'
```
:::
::::

:::: listingblock
::: content
``` highlight
{
  "test03": {
    "mappings": {
      "properties": {
        "a": {
          "type": "long"
        }
      }
    }
  }
}
```
:::
::::

::: paragraph
What if you send through a value that's not `long`?
:::

:::: listingblock
::: content
``` highlight
echo '5:{"a":"this is valid JSON but is string content"}' | \
  docker exec -i kafkacat kafkacat \
          -b broker:29092 \
          -P -t test03 -Z -K:
```
:::
::::

::: paragraph
Message doesn't arrive in Elasticsearch:
:::

:::: listingblock
::: content
``` highlight
➜ curl -s http://localhost:9200/test03/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test03","_type":"_doc","_id":"1","_score":1,"_source":{"a":1}}
{"_index":"test03","_type":"_doc","_id":"3","_score":1,"_source":{"a":3}}
```
:::
::::

::: paragraph
Check connector status
:::

:::: listingblock
::: content
``` highlight
curl -s "http://localhost:8083/connectors?expand=info&expand=status" | \
       jq '. | to_entries[] | [ .value.info.type, .key, .value.status.connector.state,.value.status.tasks[].state,.value.info.config."connector.class"]|join(":|:")' | \
       column -s : -t| sed 's/\"//g'| sort
```
:::
::::

:::: listingblock
::: content
``` highlight
sink  |  sink-elastic-test03  |  RUNNING  |  FAILED  |  io.confluent.connect.elasticsearch.ElasticsearchSinkConnector
```
:::
::::

::: paragraph
Why's it crashed?
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:8083/connectors/sink-elastic-test03/status | jq -r '.tasks[].trace'
```
:::
::::

:::: listingblock
::: content
``` highlight
org.apache.kafka.connect.errors.ConnectException: Exiting WorkerSinkTask due to unrecoverable exception.
        at org.apache.kafka.connect.runtime.WorkerSinkTask.deliverMessages(WorkerSinkTask.java:568)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.poll(WorkerSinkTask.java:326)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.iteration(WorkerSinkTask.java:228)
        at org.apache.kafka.connect.runtime.WorkerSinkTask.execute(WorkerSinkTask.java:196)
        at org.apache.kafka.connect.runtime.WorkerTask.doRun(WorkerTask.java:184)
        at org.apache.kafka.connect.runtime.WorkerTask.run(WorkerTask.java:234)
        at java.util.concurrent.Executors$RunnableAdapter.call(Executors.java:511)
        at java.util.concurrent.FutureTask.run(FutureTask.java:266)
        at java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1149)
        at java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:624)
        at java.lang.Thread.run(Thread.java:748)
Caused by: org.apache.kafka.connect.errors.ConnectException: Bulk request failed: [{"type":"mapper_parsing_exception","reason":"failed to parse field [a] of type [long] in document with id '5'. Preview of field's value: 'this is valid JSON but is string content'","caused_by":{"type":"illegal_argument_exception","reason":"For input string: \"this is valid JSON but is string content\""}}]
…
```
:::
::::

::: paragraph
Set `"behavior.on.malformed.documents" : "warn"`:
:::

:::: listingblock
::: content
``` highlight
curl -i -X PUT -H  "Content-Type:application/json" \
  http://localhost:8083/connectors/sink-elastic-test03/config \
  -d '{
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "key.converter"                   : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                 : "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable"  : "false",
    "topics"                          : "test03",
    "connection.url"                  : "http://elasticsearch:9200",
    "type.name"                       : "_doc",
    "key.ignore"                      : "false",
    "schema.ignore"                   : "true",
    "errors.tolerance"                : "all",
    "errors.log.enable"               : "true",
    "errors.log.include.messages"     : "true",
    "errors.deadletterqueue.topic.name":"dlq_sink-elastic-test03",
    "errors.deadletterqueue.topic.replication.factor": 1,
    "errors.deadletterqueue.context.headers.enable":true,
    "behavior.on.malformed.documents" : "warn"
}'
```
:::
::::

::: paragraph
Send some more data through
:::

:::: listingblock
::: content
``` highlight
echo '6:{"a":42}' | \
  docker exec -i kafkacat kafkacat \
          -b broker:29092 \
          -P -t test03 -Z -K:
```
:::
::::

::: paragraph
Pipeline is working
:::

:::: listingblock
::: content
``` highlight
curl -s http://localhost:9200/test03/_search \
    -H 'content-type: application/json' \
    -d '{ "size": 42  }' | jq -c '.hits.hits[]'
```
:::
::::

:::: listingblock
::: content
``` highlight
{"_index":"test03","_type":"_doc","_id":"1","_score":1,"_source":{"a":1}}
{"_index":"test03","_type":"_doc","_id":"3","_score":1,"_source":{"a":3}}
{"_index":"test03","_type":"_doc","_id":"6","_score":1,"_source":{"a":42}}
```
:::
::::
::::::::::::::::::::::::::::::::::::::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

::::: sect1
## Video Tutorial {#_video_tutorial}

:::: sectionbody
::: paragraph
🎥 **Check out the video tutorial here:
[https://rmoff.dev/kafka-elasticsearch-video](https://rmoff.dev/kafka-elasticsearch-video){.bare}**
:::
::::
:::::

::::: sect1
## References {#_references}

:::: sectionbody
::: ulist
-   [From Zero to Hero with Kafka
    Connect](https://rmoff.dev/crunch19-zero-to-hero-kafka-connect)

-   [Kafka Connect Elasticsearch Connector in
    Action](https://www.confluent.io/blog/kafka-elasticsearch-connector-tutorial)

-   [Tips and tricks with the Elasticsearch
    connector](https://rmoff.net/2019/10/07/kafka-connect-and-elasticsearch/)

-   [Kafka Connect Deep Dive -- Error Handling and Dead Letter
    Queues](https://www.confluent.io/blog/kafka-connect-deep-dive-error-handling-dead-letter-queues/)

-   [Confluent Hub](https://hub.confluent.io)

-   [Single Message Transform
    blog](https://www.confluent.io/blog/simplest-useful-kafka-connect-data-pipeline-world-thereabouts-part-3/)

-   [TimestampConverter](https://docs.confluent.io/current/connect/transforms/timestampconverter.html)
    Single Message Transform

-   [TimestampRouter](https://docs.confluent.io/current/connect/transforms/timestamprouter.html)
    Single Message Transform

-   [RegExRouter](https://docs.confluent.io/current/connect/transforms/regexrouter.html)
    Single Message Transform
:::
::::
:::::
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:::: {#footer}
::: {#footer-text}
Version 1.10\
Last updated 2024-06-09 00:19:53 +0300
:::
::::
