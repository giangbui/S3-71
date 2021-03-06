#!/usr/bin/env python3

import uuid
import json
import logging
import argparse
import time
import string

from shared_functions import get_config, put_sqs, check_queue, check_dead_letter

if __name__ == '__main__':

    """
    copies all files from source to destination bucket
    """

    # Logging setup
    logging.basicConfig(filename='scan.log',
                        filemode='a',
                        level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(__name__)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s %(message)s', "%H:%M:%S"))
    logger.addHandler(console)

    # Command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source_bucket",
                        help="Source Bucket Name",
                        default='test-source-keithrozario')
    parser.add_argument("-d", "--dest_bucket",
                        help="Destination Bucket Name",
                        default='test-dest-keithrozario')
    parser.add_argument("-p", "--per_lambda",
                        help="number of files to transfer per lambda",
                        default=100)
    args = parser.parse_args()

    # Get Configuration
    config = get_config()
    region = config['provider']['region']
    service_name = config['service']
    list_queue_name = config['custom']['sqs_list_bucket'].replace('${self:service}', service_name)
    copy_queue_name = config['custom']['sqs_copy_objects'].replace('${self:service}', service_name)
    logger.info(f'Copying contents of {args.source_bucket} to {args.dest_bucket}')
    logger.info(f'Using Serverless deployment {service_name}')
    logger.info(f'Using SQS Queue: {list_queue_name}, {copy_queue_name}')

    message = {"source_bucket": args.source_bucket,
               "dest_bucket": args.dest_bucket,
               "per_lambda": 50}

    prefixes = string.printable
    message_batch = []
    for prefix in prefixes:
        message['prefix'] = prefix
        message_batch.append({'MessageBody': json.dumps(message), "Id": uuid.uuid4().__str__()})

    # Putting messages onto the Que
    put_sqs(message_batch, list_queue_name)

    # Check Queue
    logger.info("No messages left on SQS Que, checking DLQ:")
    check_dead_letter(f"{service_name}-dl")

    logger.info('Checking copy Queue')
    while True:

        num_messages_on_que, num_messages_hidden = check_queue(copy_queue_name)
        if num_messages_on_que == 0 and num_messages_hidden == 0:
            break
        else:
            time.sleep(30)

    if check_dead_letter(f"{service_name}-dl") > 0:
        logger.info(f"Errors found, please refer to {service_name}-dl for more info")
    else:
        logger.info("All Done")
