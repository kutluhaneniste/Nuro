"use strict";

const fs = require("node:fs/promises");
const { parseMultipart } = require("./_multipart");
const { createJob, publicJob } = require("./_jobs");
const { runReportJob } = require("./_report");

function readField(v) {
  return Array.isArray(v) ? v[0] : v;
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }

  try {
    const { fields, files } = await parseMultipart(req);
    const file = files.file;
    if (!file) {
      res.status(400).json({ error: 'Missing form field "file"' });
      return;
    }

    const input = Array.isArray(file) ? file[0] : file;
    const zipBuffer = await fs.readFile(input.filepath);
    const originalFilename =
      readField(fields.originalFilename) || input.originalFilename || "video.mp4";

    const rec = createJob({
      zipBuffer,
      modalJobId: readField(fields.modalJobId) || null,
      modalSavedPaths: readField(fields.modalSavedPaths) || null,
      originalFilename,
    });

    setTimeout(() => {
      runReportJob(rec.id).catch(() => {});
    }, 0);

    res.status(202).json({
      jobId: rec.id,
      status: rec.status,
      job: publicJob(rec),
    });
  } catch (e) {
    res.status(500).json({ error: String(e && e.message ? e.message : e) });
  }
};

module.exports.config = {
  api: {
    bodyParser: false,
  },
};
