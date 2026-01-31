import fs from 'fs';
import path from "path"
import {NextFunction, Request, Response} from 'express';


export const getBaseDir = (): string => {
    let baseDir = "/DemoSystem"
    if (!fs.existsSync(baseDir)) {
        baseDir = './'
    }
    return path.resolve(baseDir)
}

export const replaceRelativePath = (command: string, hostProjectPath: string, condaPath: string, envName: string): string => {
    return command.replace("$hostProjectPath", hostProjectPath)
        .replace("$condaPath", condaPath)
        .replace("$envName", envName)
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