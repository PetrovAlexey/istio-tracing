import sys
import time
import logging
import random
import math
from jaeger_client import Config
from opentracing_instrumentation.request_context import get_current_span, span_in_context
import opentracing
import pika
from opentracing.propagation import Format
import functools
from opentracing.ext import tags

def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)    
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': 'localhost',
                'reporting_port': '6831',
            },
            'logging': True,
        },
        service_name=service,
    )
    return config.initialize_tracer()

def on_message(chan, method_frame, _header_frame, body, userdata=None):
    """Called when a message is received. Log message and ack it."""
    print('Userdata: %s Message body: %s', userdata, body)
    chan.basic_ack(delivery_tag=method_frame.delivery_tag)
    span = None
    carrier_dict = eval(body)
    extracted_context = tracer.extract(format=Format.TEXT_MAP, carrier=carrier_dict)
    print(extracted_context)
    if 1:
        span_tags = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
        with tracer.start_span(operation_name="Get message", child_of=extracted_context, tags = span_tags) as span:
            span.set_tag('Movie', "That's own api2!!")
            with span_in_context(span):
                time.sleep(2)
                print("All right "+str(body))
        
    else:
        print("Fatal Error "+str(body))


def booking_mgr(movie):
    
    credentials = pika.PlainCredentials('istio', 'istio')
    parameters = pika.ConnectionParameters('rabbitmq', 5672, credentials=credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue='numbers')
    on_message_callback = functools.partial(
        on_message, userdata='on_message_userdata')
    channel.basic_consume('numbers', on_message_callback)
    channel.start_consuming()

    


assert len(sys.argv) == 2
tracer = init_tracer('Consumer')
movie = sys.argv[1]
booking_mgr(movie)
# yield to IOLoop to flush the spans
time.sleep(2)
tracer.close()