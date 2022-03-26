const EventEmitter = require('./EventEmitter');
const PluginEnum = require('./PluginEnum');
const PluginInterface = require('./PluginInterface')

const supported_plugin_events = ['pendingTransactions', 'newBlockHeaders'];
const event_type = {
  settings: 'settings',
  data: 'data',
};

const settings = {
  filters: [...supported_plugin_events],
  interactions: {}, //or array
  decoration: [], // or object
};

// need to create an interface for all plugins to follow this one
class BlockchainPlugin extends PluginInterface {
  constructor() {
    super()
    this.__message_event = `message:${PluginEnum.blockchain}`;
    this.__local_emitter = EventEmitter.emitters[PluginEnum.blockchain];
    this.__settings = settings;
    this.emit({
      eventType: event_type.settings,
      data: this.__settings,
    });
  }

  emit(data) {
    console.log(`FROM type ${PluginEnum.blockchain} - emitting data ${JSON.stringify(data)} to main handler`);
    this.__local_emitter.emit(this.__message_event, JSON.stringify(data));
  }

  attach(supportedEvent) {
    // attach supported event and emit data to
    console.log(`FROM type ${PluginEnum.blockchain} - attaching event ${supportedEvent}`);

    setInterval(() => {
      //Timestamp
      // Node ID
      // Thread ID: multiple threads can be visualized using different colors
      // Event type
      // Type-specific data
      this.emit(this.structureData({
        nodeId: '',
        path: {
          source: 'source node',
          destination: 'destination node'
        },
        data: {
          event: supportedEvent,
          contractId: '',
        },
      }));
    }, 1000);
  }

  structureData(data = {}) {
    return {
      timestamp: Date.now(),
      nodeId: data.nodeId,
      path: data.path,
      eventType: event_type.data,
      data: data.data,
      //action type -> flash, highlight
    };
  }
}

module.exports = BlockchainPlugin;
