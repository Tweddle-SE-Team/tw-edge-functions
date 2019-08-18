import boto3
import base64
import pathlib
import os
from urllib.parse import urlparse

def get_analytics_page(client, analytics_addr):
  addr = urlparse(analytics_addr)
  return (
    f"<html>"
    f"  <head>"
    f"    <link rel=\"icon\" type=\"image/png\" href=\"{addr.scheme}://{addr.netloc}/favicon.png\">"
    f"    <meta http-equiv=\"Content-Type\" content=\"text/html;charset=ISO-8859-1\">"
    f"    <title>Tweddle Group Insights - {client}</title>"
    f"  </head>"
    f"  <body style=\"text-align: center; margin: 0 0 0 0;\">"
    f"    <iframe width=\"70%\" height=\"100%\" src=\"{analytics_addr}\" frameborder=\"0\" style=\"border:0\" allowfullscreen></iframe>"
    f"  </body>"
    f"</html>"
  )

def unauthorized():
  return {
    'status': '401',
    'statusDescription': 'Unauthorized',
    'body': 'Unauthorized',
    'headers': {
      'www-authenticate': [{'key': 'WWW-Authenticate', 'value':'Basic'}]
    }
  }

def analytics_response(body):
  return {
    'status': '200',
    'statusDescription': 'OK',
    'headers': {
      'cache-control': [{
        'key': 'Cache-Control',
        'value': 'max-age=100'
      }],
      'content-type': [{
        'key': 'Content-Type',
        'value': 'text/html'
      }],
      'content-encoding': [{
        'key': 'Content-Encoding',
        'value': 'UTF-8'
      }],
    },
    'body': body
  }

def parse_lambda_alias_arn(arn):
  parts = arn.split(":")
  name_parts = parts[6].split(".")
  return {
    'region': name_parts[0],
    'name': name_parts[1],
    'account_id': parts[4]
  }

def build_lambda_arn(name, region, account_id):
  return f"arn:aws:lambda:{region}:{account_id}:function:{name}"

def get_headers(raw_headers):
    headers = {}
    for header, values in raw_headers.items():
        headers[header] = []
        for value in values:
            for v in value['value'].split(","):
                headers[header].append(v)
    return headers

def handler(event, context):
  request = event["Records"][0]["cf"]["request"]
  event_type = event["Records"][0]["cf"]["config"]["eventType"]
  if event_type == "viewer-request":
      request['headers']['x-forwarded-host'] = [{ 'key': 'X-Forwarded-Host', 'value': request['headers']['host'][0]['value'] }]
  elif event_type == "origin-request":
      if 's3' in request['origin']:
          headers = get_headers(request['headers'])
          if 'x-forwarded-host' in headers:
              host = headers['x-forwarded-host'][0]
              custom_headers = get_headers(request['origin']['s3']['customHeaders'])
              if 'analytics-host' in custom_headers and host in custom_headers['analytics-host']:
                  if not 'authorization' in headers or not 'analytics-auth' in custom_headers or not headers['authorization'][0] in custom_headers['analytics-auth']:
                      return unauthorized()
                  args = parse_lambda_alias_arn(context.invoked_function_arn)
                  function_arn = build_lambda_arn(**args)
                  aws_lambda = boto3.client("lambda", region_name=args['region'])
                  response = aws_lambda.list_tags(
                    Resource=function_arn
                  )
                  tags = response['Tags']
                  client = tags['Brand'] if tags.get('Brand') else tags['Client']
                  body = get_analytics_page(client, custom_headers['analytics-addr'][0])
                  return analytics_response(body)
          else:
              if not pathlib.Path(request['uri']).suffix:
                  request['uri'] = '/index.html'
      elif request['origin'].get('custom'):
        if request['uri'].startswith("/logs"):
          if request['method'] == "POST":
            custom_headers = get_headers(request['origin']['custom']['customHeaders'])
            request['uri'] = custom_headers['ingest-path']
  return request
