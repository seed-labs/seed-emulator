import Emitter from 'event-emitter';

interface Emitters {
  [key: number]: any
}

class EventEmitter {
  static emitters:Emitters = {};
  private __type: number;
  private __local_emitter: typeof Emitter;

  constructor(type:number) {
    this.__type = type;
    this.__local_emitter = new Emitter();
    EventEmitter.emitters[type] = this.__local_emitter;
  }

  on(event:string, callback:Function) {
    this.__local_emitter.on(`${event}:${this.__type}`, callback);
  }

  once(event:string, callback:Function) {
    this.__local_emitter.once(`${event}:${this.__type}`, callback);
  }

  off(event:string, callback:Function) {
    this.__local_emitter.off(`${event}:${this.__type}`, callback);
  }

  emit(event:string, data:any) {
    this.__local_emitter.emit(`${event}:${this.__type}`, data);
  }
}

export default EventEmitter;