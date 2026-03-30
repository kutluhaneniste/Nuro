"use strict";

const { getJob } = require("../../_jobs");

module.exports = async (req, res) => {
  const { id } = req.query;
  const rec = getJob(id);
  if (!rec) {
    res.status(404).json({ error: "Job bulunamadı." });
    return;
  }
  if (!rec.zipBuffer) {
    res.status(404).json({ error: "ZIP bulunamadı." });
    return;
  }
  const safe = String(rec.originalFilename || "video")
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "_")
    .slice(0, 80);
  const name = `tribe_${safe || "video"}_${id.slice(0, 8)}.zip`;
  res.setHeader("Content-Type", "application/zip");
  res.setHeader("Content-Disposition", `attachment; filename="${name}"`);
  res.status(200).send(rec.zipBuffer);
};
