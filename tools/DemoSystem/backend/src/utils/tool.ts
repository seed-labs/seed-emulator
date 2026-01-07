import fs from 'fs';
import path from "path"
import * as os from 'os';
import {Request, Response, NextFunction} from 'express';

export const getBaseDir = (): string => {
    let baseDir = "/BaseDir"
    if (!fs.existsSync(baseDir)) {
        baseDir = './'
    }
    return path.resolve(baseDir)
}

export function getLocalIp(): string {
    let host = process.env.HOST || ''
    if (host !== '') {
        return host
    }
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        const ifaceList = interfaces[name];
        if (!ifaceList) continue;

        for (const iface of ifaceList) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }

    return '';
}

export function errorHandler(err: any, _req: Request, res: Response, _next: NextFunction): void {
    const statusCode = err.status || 500;
    const message = err.message || '内部服务器错误';

    res.status(statusCode).json({
        ok: false,
        result: message,
    });
}

export const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));