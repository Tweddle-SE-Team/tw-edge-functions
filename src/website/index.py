import boto3
import base64
import pathlib
import os

def get_analytics_page(client, baseUrl, path):
  return (
    f"<html>"
    f"  <head>"
    f"    <link rel=\"icon\" type=\"image/png\" href=\"{baseUrl}/favicon.png\">"
    f"    <meta http-equiv=\"Content-Type\" content=\"text/html;charset=ISO-8859-1\">"
    f"    <title>Tweddle Group Insights - {client}</title>"
    f"  </head>"
    f"  <body style=\"text-align: center; margin: 0 0 0 0;\">"
    f"    <iframe width=\"70%\" height=\"100%\" src=\"{baseUrl}{path}\" frameborder=\"0\" style=\"border:0\" allowfullscreen></iframe>"
    f"  </body>"
    f"</html>"
  )

def get_expected_authorize_header(path, region):
  ssm = boto3.client('ssm', region_name=region)
  response = ssm.get_parameters_by_path(
    Path=path,
    Recursive=True,
    WithDecryption=True)
  credentials = {os.path.basename(param['Name']): param['Value'] for param in response['Parameters']}
  hash_value = base64.b64encode(bytes(f"{credentials['username']}:{credentials['password']}", "utf-8")).decode("utf-8")
  return f"Basic {hash_value}"

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

def handler(event, context):
  request = event["Records"][0]["cf"]["request"]
  if request['origin'].get('s3'):
    if not pathlib.Path(request['uri']).suffix:
      request['uri'] = '/index.html'
  elif request['origin'].get('custom'):
    if request['uri'].startswith("/logs"):
      if request['method'] == "POST":
        request['uri'] = request['origin']['custom']['path']
    elif request['uri'].startswith("/analytics"):
      args = parse_lambda_alias_arn(context.invoked_function_arn)
      function_arn = build_lambda_arn(**args)
      analytics_url = f"{request['origin']['custom']['protocol']}://{request['origin']['custom']['domainName']}"
      analytics_path = request['origin']['custom']['path']
      aws_lambda = boto3.client("lambda", region_name=args['region'])
      response = aws_lambda.list_tags(
        Resource=function_arn
      )
      tags = response['Tags']
      client = tags['Brand'] if tags.get('Brand') else tags['Client']
      path = f"/{tags['Component']}/{tags['Environment']}/common/gds"
      auth_value = get_expected_authorize_header(path, args['region'])
      if not request['headers'].get('authorization') or request['headers']['authorization'][0]['value'] != auth_value:
        return {
          'status': '401',
          'statusDescription': 'Unauthorized',
          'body': 'Unauthorized',
          'headers': {
            'www-authenticate': [{'key': 'WWW-Authenticate', 'value':'Basic'}]
          },
        }
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
        'body': get_analytics_page(client, analytics_url, analytics_path)
      }
  return request
