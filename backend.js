const express = require("express");
const { spawn } = require("child_process");
const cors = require("cors");
const path = require("path");

const app = express();
const PORT = 5000;

app.use(cors({
  origin: 'http://localhost:3000',
  methods: ['GET'],
  allowedHeaders: ['Content-Type']
}));

app.get("/api/run-script-stream", (req, res) => {
  const video_url = req.query.video_url;
  const step = req.query.step;

  if (!video_url) {
    return res.status(400).send("Missing video_url");
  }

  const scriptPath = path.resolve(__dirname, "shorts_automation.py");
  const stepArg = step ? ["--step", step] : [];
  const pythonPath = path.resolve(__dirname, ".venv/bin/python3.10"); // or just "python3"

  const child = spawn(pythonPath, ['-u', scriptPath, video_url, ...stepArg]);
  
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  child.stdout.on("data", (data) => {
    const lines = data.toString().split("\n");
    lines.forEach(line => {
      if (line.trim()) {
        res.write(`data: ${line.trim()}\n\n`);
      }
    });
  });

  child.stderr.on("data", (data) => {
    const lines = data.toString().split("\n");
    lines.forEach(line => {
      if (line.trim()) {
        res.write(`data: ⚠️ ${line.trim()}\n\n`);
      }
    });
  });

  child.on("close", (code) => {
    res.write(`data: ✅ Script finished with code ${code}\n\n`);
    res.write("event: done\ndata: end\n\n");
    res.end();
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Backend running at http://localhost:${PORT}`);
});