import EventEmitter from '../../../common/EventEmitter';
import PluginEnum from '../../../common/PluginEnum';

const supported_plugins = [...Object.values(PluginEnum)];


class BasePlugin {
  private __type: Number;
  private __local_emitter: EventEmitter;
  private __plugin: any;
  
  constructor(type) {

    if (!supported_plugins.includes(type)) {
      throw new Error('Plugin type not supported');
    }
    this.__type = type;
    this.__local_emitter = new EventEmitter(type);
  }

  run() {
    // find a way to run/fetch modules based type
    if (this.__type === PluginEnum.blockchain) {
      //const plugin = require('./blockchainPluginSimulator');
      //this.__plugin = new plugin();
      console.log("created plugin of type blockchain")
    }
  }

  attach(filter:string, params:string) {
    this.__plugin.attach(`${filter}`, params);
  }

  onMessage(callback:Function) {
    this.__local_emitter.on('message', callback);
  }

  onError(callback:Function) {
    this.__local_emitter.on('error', callback);
  }

  getType() {
    return this.__type;
  }
}

export default BasePlugin;