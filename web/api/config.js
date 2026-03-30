/**
 * Vercel serverless: ortamdan varsayılan Modal kök URL döner.
 * Vercel Dashboard → Settings → Environment Variables → TRIBE_API_URL
 */
module.exports = (req, res) => {
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.status(200).json({
    TRIBE_API_URL: (process.env.TRIBE_API_URL || "").trim(),
  });
};
