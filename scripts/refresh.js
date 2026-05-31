const fs = require("fs");
const { exec } = require("child_process");

const data = JSON.parse(fs.readFileSync("../link.json"));

for (const ch of data) {
  exec(`yt-dlp -g "https://www.youtube.com/watch?v=${ch.id}"`, (err, out) => {
    if (!err) {
      console.log(ch.name, out.toString().split("\n")[0]);
    }
  });
}
