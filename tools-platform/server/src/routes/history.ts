import { Router } from 'express';
import { getRecentHistory } from '../controllers/historyController';

const router = Router();
router.get('/recent', getRecentHistory);

export default router;
