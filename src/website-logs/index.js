exports.handler = (evt, ctx, cb) => {
   const request = evt.Records[0].cf.request;
   if (request.method === 'POST') {
      request.uri = "/noformat/logs/${token}";
   }
   return cb(null, request);
}
