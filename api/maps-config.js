// Vercel Node function for the Stouro Tour map. It hands the browser the Google Maps *browser* key from
// Vercel Environment Variables so no key is committed to source control. Browser keys are visible to
// clients by design: restrict GOOGLE_MAPS_BROWSER_KEY to your HTTP referrers and the Maps JavaScript API.
// GOOGLE_MAPS_MAP_ID is optional; a vector Map ID enables heading-up map rotation.
module.exports = function mapsConfig(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Method not allowed' });
  }
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    key: (process.env.GOOGLE_MAPS_BROWSER_KEY || '').trim(),
    mapId: (process.env.GOOGLE_MAPS_MAP_ID || '').trim()
  });
};
