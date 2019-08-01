const path = require('path')
const { STATUS_CODES } = require('http')
const whitelist = []
exports.handler = (evt, ctx, cb) => {

  const { request } = evt.Records[0].cf
  if (!path.extname(request.uri) || whitelist.filter((rule) => request.uri.startsWith(rule)).length > 0) {
      request.uri = '/index.html'
  }
  cb(null, request)
}
