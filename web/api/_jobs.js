"use strict";

const { randomUUID } = require("node:crypto");

const jobs = new Map();

function nowIso() {
  return new Date().toISOString();
}

function createJob(payload) {
  const id = randomUUID();
  const rec = {
    id,
    status: "queued",
    createdAt: nowIso(),
    updatedAt: nowIso(),
    error: null,
    reportMarkdown: null,
    reportSummary: null,
    metadata: null,
    predsSummary: null,
    zipBuffer: payload.zipBuffer,
    zipSize: payload.zipBuffer ? payload.zipBuffer.length : 0,
    modalJobId: payload.modalJobId || null,
    modalSavedPaths: payload.modalSavedPaths || null,
    originalFilename: payload.originalFilename || "video",
  };
  jobs.set(id, rec);
  return rec;
}

function getJob(id) {
  return jobs.get(id) || null;
}

function updateJob(id, patch) {
  const rec = jobs.get(id);
  if (!rec) return null;
  Object.assign(rec, patch, { updatedAt: nowIso() });
  return rec;
}

function publicJob(rec) {
  if (!rec) return null;
  return {
    id: rec.id,
    status: rec.status,
    createdAt: rec.createdAt,
    updatedAt: rec.updatedAt,
    error: rec.error,
    reportMarkdown: rec.reportMarkdown,
    reportSummary: rec.reportSummary,
    metadata: rec.metadata,
    predsSummary: rec.predsSummary,
    zipSize: rec.zipSize,
    modalJobId: rec.modalJobId,
    modalSavedPaths: rec.modalSavedPaths,
    originalFilename: rec.originalFilename,
  };
}

module.exports = {
  createJob,
  getJob,
  updateJob,
  publicJob,
};
