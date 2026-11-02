const express = require('express');
const router = express.Router();
const { getGlobalStats } = require('../db/database');

/**
 * GET /api/stats
 * Returns global analytical statistics from database
 */
router.get('/', async (req, res) => {
  try {
    const stats = await getGlobalStats();
    return res.json({
      success: true,
      data: stats
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: 'Failed to retrieve analytics statistics from database.'
    });
  }
});

module.exports = router;
