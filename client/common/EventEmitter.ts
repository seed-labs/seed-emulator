import {EventEmitter as Emitter} from 'events';
// import PluginEnum from './PluginEnum';

interface Emitters {
  [key:number]: Emitter
}

class EventEmitter {
  static emitters:Emitters = {}
  private __type: number;
  private __local_emitter: Emitter;

  constructor(type:number) {
    this.__type = type;
    this.__local_emitter = new Emitter();
    EventEmitter.emitters[type] = this.__local_emitter;
  }

  on(event:string, callback:(...args: any[]) => void) {
    this.__local_emitter.on(`${event}:${this.__type}`, callback);
  }

  once(event:string, callback:(...args: any[]) => void) {
    this.__local_emitter.once(`${event}:${this.__type}`, callback);
  }

  off(event:string, callback:(...args: any[]) => void) {
    this.__local_emitter.off(`${event}:${this.__type}`, callback);
  }

  emit(event:string, data:any) {
    this.__local_emitter.emit(`${event}:${this.__type}`, data);
  }
}

export default EventEmitter;