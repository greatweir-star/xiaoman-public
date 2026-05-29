import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const DIST = path.join(__dirname, 'dist');

const mime = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
};

const srv = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url === '/' ? '/index.html' : req.url);
  let file = path.join(DIST, urlPath);
  const ext = path.extname(file);
  fs.readFile(file, (err, data) => {
    if (err) {
      console.error(`404: ${urlPath}`);
      res.writeHead(404);
      res.end('404');
      return;
    }
    res.writeHead(200, { 'Content-Type': mime[ext] || 'text/plain' });
    res.end(data);
  });
});

srv.listen(PORT, () => console.log(`http://localhost:${PORT}`));
