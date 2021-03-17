import { Logger } from 'tslog';

export interface LogProducer {
    getLoggers(): Logger[];
}