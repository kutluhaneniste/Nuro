"use strict";

const formidablePkg = require("formidable");

const IncomingForm =
  formidablePkg.IncomingForm ||
  formidablePkg.Formidable ||
  (formidablePkg.default && formidablePkg.default.IncomingForm);

function parseMultipart(req) {
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

module.exports = { parseMultipart };
