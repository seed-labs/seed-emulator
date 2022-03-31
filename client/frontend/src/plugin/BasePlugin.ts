import EventEmitter from '../../../common/EventEmitter';
import PluginEnum from './PluginEnum';
import BlockchainPlugin from './BlockchainPlugin';

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
      this.__plugin = new BlockchainPlugin();
      console.log("created plugin of type blockchain")
    }
  }

  attach(filter:string, params:string) {
    this.__plugin.attach(`${filter}`, params);
  }

  onMessage(callback:(...args: any[]) => void) {
    this.__local_emitter.on('message', callback);
  }

  onError(callback:(...args: any[]) => void) {
    this.__local_emitter.on('error', callback);
  }

  getType() {
    return this.__type;
  }
}

export default BasePlugin;