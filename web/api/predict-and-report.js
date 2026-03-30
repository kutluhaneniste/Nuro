"use strict";

const formidablePkg = require("formidable");
/**
 * Vercel / farklı bundler’larda factory export kaybolabiliyor.
 * `IncomingForm` doğrudan sınıf — her zaman CJS build’inde var.
 */
const IncomingForm =
  formidablePkg.IncomingForm ||
  formidablePkg.Formidable ||
  (formidablePkg.default && formidablePkg.default.IncomingForm);
const { createJob, publicJob } = require("./_jobs");
const { runReportJob } = require("./_report");

function parseForm(req) {
  if (typeof IncomingForm !== "function") {
    return Promise.reject(
      new Error(
        "formidable.IncomingForm yüklenemedi (paket: " + typeof formidablePkg + ")"
      )
    );
  }
  const form = new IncomingForm({
    multiples: false,
    maxFileSize: 1024 * 1024 * 1024,
  });
  return new Promise((resolve, reject) => {
    form.parse(req, (err, fields, files) => {
      if (err) reject(err);
      else resolve({ fields, files });
    });
  });
}

function normalizeBase(u) {
  return String(u || "").trim().replace(/\/+$/, "");
}

function readField(v) {
  return Array.isArray(v) ? v[0] : v;
}

function headerApiKey(req) {
  const h = req.headers || {};
  const v = h["x-api-key"] || h["X-API-Key"];
  return typeof v === "string" ? v.trim() : "";
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }

  try {
    const { fields, files } = await parseForm(req);
    const file = files.file;
    if (!file) {
      res.status(400).json({ error: 'Missing form field "file"' });
      return;
    }

    const input = Array.isArray(file) ? file[0] : file;
    const fs = require("node:fs/promises");
    const videoBuffer = await fs.readFile(input.filepath);
    const originalFilename = input.originalFilename || "video.mp4";

    const modalBase = normalizeBase(readField(fields.modalBaseUrl) || process.env.TRIBE_API_URL || "");
    if (!modalBase) {
      res.status(400).json({ error: "Modal URL eksik (modalBaseUrl veya TRIBE_API_URL)." });
      return;
    }

    const headers = {};
    const upstreamKey = (
      process.env.TRIBE_UPSTREAM_API_KEY ||
      headerApiKey(req) ||
      ""
    ).trim();
    if (upstreamKey) headers["X-API-Key"] = upstreamKey;

    const upstreamForm = new FormData();
    upstreamForm.append("file", new Blob([videoBuffer]), originalFilename);

    const upstream = await fetch(`${modalBase}/predict`, {
      method: "POST",
      headers,
      body: upstreamForm,
    });
    const zipBuffer = Buffer.from(await upstream.arrayBuffer());
    if (!upstream.ok) {
      const detail = zipBuffer.toString("utf8").slice(0, 2000);
      res.status(upstream.status).json({ error: `Modal hata: ${detail}` });
      return;
    }

    const rec = createJob({
      zipBuffer,
      modalJobId: upstream.headers.get("X-Tribe-Job-Id"),
      modalSavedPaths: upstream.headers.get("X-Tribe-Saved-Paths"),
      originalFilename,
    });

    setTimeout(() => {
      runReportJob(rec.id).catch(() => {});
    }, 0);

    res.status(202).json({
      jobId: rec.id,
      status: rec.status,
      modalJobId: rec.modalJobId,
      modalSavedPaths: rec.modalSavedPaths,
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
