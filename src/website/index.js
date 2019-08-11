const path = require('path')
const { STATUS_CODES } = require('http')
const AWS = require('aws-sdk');

function GetAnalyticsPage(client, baseUrl, path) {
   return `
<html>
<head>
  <link rel="icon"
        type="image/png"
        href="${baseUrl}/favicon.png">
  <meta http-equiv="Content-Type"
        content="text/html;charset=ISO-8859-1">
  <title>Tweddle Group Insights - ${client}</title>
</head>
<body style="text-align: center; margin: 0 0 0 0;">
<iframe width="70%" height="100%" src="${baseUrl}${path}" frameborder="0" style="border:0" allowfullscreen></iframe>
</body>
</html>
`;
}

const whitelist = []
exports.handler = (evt, ctx, cb) => {
   const { request } = evt.Records[0].cf
   if (request.origin.hasOwnProperty('s3')) {
      if (!path.extname(request.uri) || whitelist.filter((rule) => request.uri.startsWith(rule)).length > 0) {
         request.uri = '/index.html'
      }
      return cb(null, request);
   } else if (request.origin.hasOwnProperty('custom')) {
      if (request.uri.startsWith("/logs")) {
         if (request.method === 'POST') {
            request.uri = request.origin.custom.path;
         }
         return cb(null, request);
      } else if (request.uri.startsWith("/analytics")) {
         const { invokedFunctionArn } = ctx
         const arnParts = invokedFunctionArn.split(":")
         const fnNameParts = arnParts[6].split(".")
         const functionArn = `arn:aws:lambda:${fnNameParts[0]}:${arnParts[4]}:function:${fnNameParts[1]}`
         const analyticsUrl = `${request.origin.custom.protocol}://${request.origin.custom.domainName}`
         const analyticsPath = `${request.origin.custom.path}`
         AWS.config.update({region: fnNameParts[0]});
         var lambda = new AWS.Lambda();
         var params = {
           Resource: functionArn
         };
         lambda.listTags(params, function(err, data) {
            if (err) {
               console.log(err, err.stack);
            } else {
               var client = data.Tags['Brand'] != null ? data.Tags['Brand'] : data.Tags['Client']
               const response = {
                  status: '200',
                  statusDescription: 'OK',
                  headers: {
                     'cache-control': [{
                         key: 'Cache-Control',
                         value: 'max-age=100'
                     }],
                     'content-type': [{
                         key: 'Content-Type',
                         value: 'text/html'
                     }],
                     'content-encoding': [{
                         key: 'Content-Encoding',
                         value: 'UTF-8'
                     }],
                  },
                  body: GetAnalyticsPage(client, analyticsUrl, analyticsPath),
               };
               return cb(null, response);
            }
         });
      }
   }
}
