const EventEmitter = require('./EventEmitter');
const PluginEnum = require('./PluginEnum');

class Plugin {
  constructor(type) {
    if (!Plugin.supported_plugins.includes(type)) {
      throw new Error('Plugin type not supported');
    }
    this.__type = type;
    this.__local_emitter = new EventEmitter(type);
  }

  run() {
    // find a way to run/fetch modules based type
    if (this.__type === PluginEnum.blockchain) {
      const plugin = require('./blockchainPluginSimulator');
      this.__plugin = new plugin();
    }
  }

  attach(filter) {
    this.__plugin.attach(`${filter}`);
  }

  onMessage(callback) {
    this.__local_emitter.on('message', callback);
  }

  onError(callback) {
    this.__local_emitter.on('error', callback);
  }

  getType() {
    return this.__type;
  }
}

Plugin.supported_plugins = [...Object.values(PluginEnum)];

module.exports = Plugin;
