import requests

def insert_into_ksqldb():
    # Define the ksqlDB server URL
    ksqldb_url = 'http://localhost:8088/ksql'  # Replace with your ksqlDB server URL and port

    # Define the SQL statement
    sql_statement = """
    INSERT INTO TEST02 (COL0, COL1, ORDER_TS_EPOCH, SHIP_TS_STR)
    VALUES ('MY_KEY__Z',
            1,
            STRINGTOTIMESTAMP('2020-02-05T11:20:00Z','yyyy-MM-dd''T''HH:mm:ssX'),
            '2020-02-05T11:20:00Z');
    """

    # Prepare the payload for the HTTP request
    payload = {
        "ksql": sql_statement,
        "streamsProperties": {}
    }

    # Perform the HTTP POST request to insert data into ksqlDB
    response = requests.post(ksqldb_url, json=payload)

    # Check if the request was successful
    if response.status_code == 200:
        print("Data inserted successfully.")
    else:
        print("Failed to insert data. Status code:", response.status_code)
        print("Response:", response.text)

if __name__ == "__main__":
    insert_into_ksqldb()
