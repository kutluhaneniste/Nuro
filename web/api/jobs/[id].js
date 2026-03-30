"use strict";

const { getJob, publicJob } = require("../_jobs");

module.exports = async (req, res) => {
  const { id } = req.query;
  const rec = getJob(id);
  if (!rec) {
    res.status(404).json({ error: "Job bulunamadı." });
    return;
  }
  res.status(200).json(publicJob(rec));
};
