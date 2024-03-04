import { Logger } from 'tslog';

export interface ILogObj
{
    name: string;
}


/**
 * common interface for object producing logs.
 */
export interface LogProducer {

    /**
     * get loggers.
     * 
     * @returns loggers.
     */
    getLoggers(): Logger<ILogObj>[];
}