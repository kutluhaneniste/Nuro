"use strict";

const JSZip = require("jszip");
const npy = require("numpy-parser");
const Anthropic = require("@anthropic-ai/sdk");
const { getJob, updateJob } = require("./_jobs");

function asArrayBuffer(buf) {
  return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
}

function toFlatNumberArray(typed) {
  if (!typed || typeof typed.length !== "number") return [];
  const out = new Array(typed.length);
  for (let i = 0; i < typed.length; i += 1) out[i] = Number(typed[i]);
  return out;
}

function stats(values) {
  if (!values.length) {
    return { count: 0, min: null, max: null, mean: null, std: null };
  }
  let min = values[0];
  let max = values[0];
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    const v = values[i];
    if (v < min) min = v;
    if (v > max) max = v;
    sum += v;
  }
  const mean = sum / values.length;
  let sq = 0;
  for (let i = 0; i < values.length; i += 1) {
    const d = values[i] - mean;
    sq += d * d;
  }
  return {
    count: values.length,
    min,
    max,
    mean,
    std: Math.sqrt(sq / values.length),
  };
}

async function parseZip(zipBuffer) {
  const z = await JSZip.loadAsync(zipBuffer);
  const metadataFile = z.file("metadata.json");
  const predsFile = z.file("preds.npz");
  if (!metadataFile || !predsFile) {
    throw new Error("ZIP içinde metadata.json veya preds.npz eksik.");
  }

  const metadataText = await metadataFile.async("string");
  const metadata = JSON.parse(metadataText);

  const predsNpzBuffer = await predsFile.async("nodebuffer");
  const npz = await JSZip.loadAsync(predsNpzBuffer);
  const entries = Object.keys(npz.files).filter((k) => k.endsWith(".npy"));
  if (!entries.length) {
    throw new Error("preds.npz içinde .npy veri bulunamadı.");
  }

  const firstKey = entries[0];
  const npyBuffer = await npz.file(firstKey).async("nodebuffer");
  const parsed = npy.fromArrayBuffer(asArrayBuffer(npyBuffer));
  const values = toFlatNumberArray(parsed.data);
  const summary = {
    sourceNpy: firstKey,
    dtype: String(parsed.dtype || metadata.preds_dtype || "unknown"),
    shape: parsed.shape || metadata.preds_shape || [],
    ...stats(values),
  };

  return { metadata, predsSummary: summary };
}

function buildPrompt(input) {
  return [
    "Aşağıdaki TRIBE v2 çıkarım özetinden kısa, teknik ve klinik iddia içermeyen bir rapor üret.",
    "Yanıt dili Türkçe olsun.",
    "Format:",
    "1) Kısa Özet (3-5 madde)",
    "2) Teknik Bulgular (madde madde)",
    "3) Sınırlar / Uyarılar",
    "4) Sonraki Adımlar",
    "",
    "Veri:",
    JSON.stringify(input, null, 2),
  ].join("\n");
}

async function generateReportWithClaude(payload) {
  const key = (process.env.ANTHROPIC_API_KEY || "").trim();
  if (!key) throw new Error("ANTHROPIC_API_KEY tanımlı değil.");

  const client = new Anthropic({ apiKey: key });
  const model = (process.env.ANTHROPIC_MODEL || "claude-opus-4-1").trim();
  const msg = await client.messages.create({
    model,
    max_tokens: 1200,
    temperature: 0.2,
    messages: [{ role: "user", content: buildPrompt(payload) }],
  });
  const textParts = (msg.content || [])
    .filter((x) => x.type === "text")
    .map((x) => x.text)
    .filter(Boolean);
  const text = textParts.join("\n\n").trim();
  if (!text) throw new Error("Claude boş rapor döndürdü.");
  return text;
}

async function runReportJob(jobId) {
  const rec = getJob(jobId);
  if (!rec) throw new Error("Job bulunamadı.");
  if (rec.status === "running" || rec.status === "done") return rec;

  updateJob(jobId, { status: "running", error: null });
  try {
    const parsed = await parseZip(rec.zipBuffer);
    const report = await generateReportWithClaude({
      metadata: parsed.metadata,
      predsSummary: parsed.predsSummary,
      originalFilename: rec.originalFilename,
    });
    return updateJob(jobId, {
      status: "done",
      metadata: parsed.metadata,
      predsSummary: parsed.predsSummary,
      reportMarkdown: report,
      reportSummary: "Rapor hazır.",
    });
  } catch (e) {
    return updateJob(jobId, {
      status: "error",
      error: String(e && e.message ? e.message : e),
    });
  }
}

module.exports = {
  runReportJob,
};
