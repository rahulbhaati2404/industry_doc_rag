const http = require("http");
const fs = require("fs");
const path = require("path");

const HOST = process.env.FRONTEND_HOST || "127.0.0.1";
const PORT = Number(process.env.FRONTEND_PORT || 5173);
const API_TARGET = process.env.API_TARGET || "http://127.0.0.1:8000";
const ROOT = __dirname;

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
};

function serveStatic(request, response) {
  const requestUrl = new URL(request.url, `http://${request.headers.host}`);
  const cleanPath = decodeURIComponent(requestUrl.pathname);
  const filePath = cleanPath === "/" ? path.join(ROOT, "index.html") : path.join(ROOT, cleanPath);
  const resolvedPath = path.resolve(filePath);

  if (!resolvedPath.startsWith(ROOT)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  fs.readFile(resolvedPath, (error, content) => {
    if (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }

    const ext = path.extname(resolvedPath);
    response.writeHead(200, { "Content-Type": contentTypes[ext] || "application/octet-stream" });
    response.end(content);
  });
}

function proxyApi(request, response) {
  const targetUrl = new URL(request.url, API_TARGET);
  const headers = { ...request.headers, host: targetUrl.host };

  const proxyRequest = http.request(
    targetUrl,
    {
      method: request.method,
      headers,
    },
    (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode || 500, proxyResponse.headers);
      proxyResponse.pipe(response);
    }
  );

  proxyRequest.on("error", (error) => {
    response.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ status: "error", message: error.message }));
  });

  request.pipe(proxyRequest);
}

const server = http.createServer((request, response) => {
  if (request.url.startsWith("/api/")) {
    proxyApi(request, response);
    return;
  }

  serveStatic(request, response);
});

server.listen(PORT, HOST, () => {
  console.log(`Frontend running at http://${HOST}:${PORT}`);
  console.log(`Proxying API requests to ${API_TARGET}`);
});
