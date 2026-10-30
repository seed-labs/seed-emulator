import express from 'express';
import {spawn} from "child_process"
import dockerRouter from './docker/index';

const router = express.Router();
router.get('/env.js', (req, res, next) => {
    const envVarsForFrontend = {
        CONSOLE: process.env.CONSOLE,
    };
    res.setHeader('Content-Type', 'application/javascript');
    res.send(`window.__ENV__ = ${JSON.stringify(envVarsForFrontend)}`);

    next();
});
router.use('/docker', dockerRouter);
export default router;
