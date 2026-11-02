const express = require('express');
const router = express.Router();
const { getRecentHistory, getTraceById, clearHistory } = require('../db/database');

/**
 * GET /api/history
 * Returns recent trace history records from database
 */
router.get('/', async (req, res) => {
  try {
    const limit = req.query.limit ? parseInt(req.query.limit, 10) : 20;
    const history = await getRecentHistory(limit);
    return res.json({
      success: true,
      count: history.length,
      data: history
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: 'Failed to retrieve history from database.'
    });
  }
});

/**
 * GET /api/history/:id
 * Retrieves full trace record by ID from database
 */
router.get('/:id', async (req, res) => {
  try {
    const record = await getTraceById(req.params.id);
    if (!record) {
      return res.status(404).json({
        success: false,
        error: `Trace record ID ${req.params.id} not found in database.`
      });
    }
    return res.json({
      success: true,
      data: record
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: 'Failed to retrieve trace record from database.'
    });
  }
});

/**
 * DELETE /api/history
 * Clears history logs from database
 */
router.delete('/', async (req, res) => {
  try {
    const success = await clearHistory();
    return res.json({
      success,
      message: 'History successfully cleared from database.'
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: 'Failed to clear database history.'
    });
  }
});

module.exports = router;
