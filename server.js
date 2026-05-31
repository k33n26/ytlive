const express = require("express");
const fs = require("fs");
const { exec } = require("child_process");

const app = express();

const CACHE_FILE = "./cache.json";

function loadCache() {
  if (!fs.existsSync(CACHE_FILE)) return {};
  return JSON.parse(fs.readFileSync(CACHE_FILE));
}

function saveCache(data) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(data, null, 2));
}

// YouTube resolve
function resolve(id, cb) {
  const cache = loadCache();

  if (cache[id] && cache[id].expire > Date.now()) {
    return cb(cache[id].url);
  }

  const cmd = `yt-dlp -g "https://www.youtube.com/watch?v=${id}"`;

  exec(cmd, { maxBuffer: 1024 * 1024 * 10 }, (err, out) => {
    if (err) return cb(null);

    const url = out.toString().split("\n")[0].trim();

    if (!url) return cb(null);

    cache[id] = {
      url,
      expire: Date.now() + 60 * 1000
    };

    saveCache(cache);
    cb(url);
  });
}

// PLAY endpoint
app.get("/play/:id", (req, res) => {
  resolve(req.params.id, (url) => {
    if (!url) {
      return res.status(404).json({ error: "stream not found" });
    }
    res.redirect(url);
  });
});

// CHANNELS JSON
app.get("/channels", (req, res) => {
  res.json(JSON.parse(fs.readFileSync("./link.json")));
});

// IPTV M3U
app.get("/playlist.m3u", (req, res) => {
  const channels = JSON.parse(fs.readFileSync("./link.json"));

  let m3u = "#EXTM3U\n";

  for (const ch of channels) {
    m3u += `#EXTINF:-1,${ch.name}\n`;
    m3u += `http://${req.hostname}:3000/play/${ch.id}\n`;
  }

  res.setHeader("content-type", "text/plain");
  res.send(m3u);
});

app.listen(3000, "0.0.0.0", () => {
  console.log("ytlive IPTV engine running");
});
