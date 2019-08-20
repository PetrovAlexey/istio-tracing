import logging
import sys
import random
import time 
import opentracing
import pika
from os import getenv
from textblob import TextBlob
from flask import Flask, request, jsonify
from flask_api import status
from flask_opentracing import FlaskTracer
from jaeger_client import Config
from opentracing_instrumentation.request_context import get_current_span, span_in_context
from flask import _request_ctx_stack as stack

JAEGER_HOST = 'localhost'
JAEGER_SERVICE_NAME = 'Producer'

app = Flask(__name__)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

config = Config(config={'sampler': {'type': 'const', 'param': 1},
                        'logging': True,
                        'propagation': 'b3',
                        'local_agent':
                            {'reporting_host': JAEGER_HOST}},
                service_name=JAEGER_SERVICE_NAME)

jaeger_tracer = config.initialize_tracer()
tracer = FlaskTracer(jaeger_tracer, True, app, ['url'])


@app.route("/analyse")
@tracer.trace()
def analyse_sentiment():
    span = tracer.get_span()
    request = stack.top.request
    headers = {}
    for k, v in request.headers:
        headers[k.lower()] = v

    tracer._tracer.inject(span.context,
                              opentracing.Format.TEXT_MAP,
                              headers)
    span_ctx = tracer._tracer.extract(opentracing.Format.TEXT_MAP, headers)
    with tracer._tracer.start_span('Send Message', child_of=span_ctx) as span:
        time.sleep(2)
        credentials = pika.PlainCredentials('istio', 'istio')
        conn_params = pika.ConnectionParameters('rabbitmq', 5672,'/', credentials)
        connection = pika.BlockingConnection(conn_params)
        channel = connection.channel()
        channel.queue_declare(queue='numbers')
        channel.basic_publish(exchange='', routing_key='numbers', body=str(headers))
        connection.close()

        return str(headers), 200 



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)