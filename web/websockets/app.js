var fs = require('fs');

var app = require('https').createServer({
    cert: fs.readFileSync('/etc/pki/tls/certs/iplantc.org.crt'), 
    key: fs.readFileSync('/etc/pki/tls/private/howe.key')
}, handler);

var io = require('socket.io').listen(app);

app.listen(8080);

function handler (req, res) {
    fs.readFile(__dirname + '/index.html', function (err, data) {
        if (err) {
            res.writeHead(500);
            return res.end('Error loading index.html');
        }
        res.writeHead(200);
        res.end(data);
    });
}

io.sockets.on('connection', function (socket) {
    socket.on('log', function (data) {
        socket.broadcast.emit('newlog', data);
    });
});
