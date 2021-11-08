const helpers = {

	demuxStream(stream, output, error) {
		return new Promise((resolve, reject) => {
			let output = '';
			let error = '';
			let nextDataType = null;
  			let nextDataLength = null;
  			let buffer = Buffer.from('');
  			function processData(data) {
    				if (data) {
      					buffer = Buffer.concat([buffer, data]);
    				}
    				if (!nextDataType) {
      					if (buffer.length >= 8) {
        					let header = bufferSlice(8);
        					nextDataType = header.readUInt8(0);
        					nextDataLength = header.readUInt32BE(4);
        					// It's possible we got a "data" that contains multiple messages
        					// Process the next one
        					processData();
      					}
    				} else {
      					if (buffer.length >= nextDataLength) {
        					let content = bufferSlice(nextDataLength);
        					if (nextDataType === 1) {
							output += content;
        					} else {
							error += content
        					}
        					nextDataType = null;
        					// It's possible we got a "data" that contains multiple messages
        					// Process the next one
       						processData();
      					}
   				}
  			}
	
	  		function bufferSlice(end) {
	    			let out = buffer.slice(0, end);
	    			buffer = Buffer.from(buffer.slice(end, buffer.length));
	    			return out;
			}
			stream.on('data', (data) => {
				processData(data)
				resolve({error: !!error, data: !!error ? error : output});
			})
		})
	}
}

module.exports = helpers;
