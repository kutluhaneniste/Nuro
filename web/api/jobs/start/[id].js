"use strict";

const { getJob, publicJob } = require("../../_jobs");
const { runReportJob } = require("../../_report");

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const { id } = req.query;
  const rec = getJob(id);
  if (!rec) {
    res.status(404).json({ error: "Job bulunamadı." });
    return;
  }
  const updated = await runReportJob(id);
  res.status(200).json(publicJob(updated));
};
