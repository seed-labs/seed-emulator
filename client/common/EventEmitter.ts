const Emitter = require('event-emitter');

class EventEmitter {
  static emitters = {};

  constructor(type) {
    this.__type = type;
    this.__local_emitter = new Emitter();
    EventEmitter.emitters[type] = this.__local_emitter;
  }

  on(event, callback) {
    this.__local_emitter.on(`${event}:${this.__type}`, callback);
  }

  once(event, callback) {
    this.__local_emitter.once(`${event}:${this.__type}`, callback);
  }

  off(event, callback) {
    this.__local_emitter.off(`${event}:${this.__type}`, callback);
  }

  emit(event, data = {}) {
    this.__local_emitter.emit(`${event}:${this.__type}`, data);
  }
}

module.exports = EventEmitter;
