import EventEmitter from './EventEmitter';
import PluginEnum from './PluginEnum';
import PluginInterface from './PluginInterface';

const supported_plugin_events = ['pendingTransactions', 'newBlockHeaders'];

const event_type = {
  settings: 'settings',
  data: 'data',
};

const settings = {
  filters: [...supported_plugin_events],
};

// need to create an interface for all plugins to follow this one
class BlockchainPlugin implements PluginInterface {
  private __message_event: string;
  private __local_emitter: any;
  private __accountsToContainerMap: object;
  private __settings: {
    filters: string[];
  };
  
  constructor() {
    this.__message_event = `message:${PluginEnum.blockchain}`;
    this.__local_emitter = EventEmitter.emitters[PluginEnum.blockchain];
    this.__settings = settings;
    this.__accountsToContainerMap = {};
    this.emit({
      eventType: event_type.settings,
      data: this.__settings,
    });
  }

  emit(data:object) {
    console.log(`FROM type ${PluginEnum.blockchain} - emitting data ${JSON.stringify(data)} to main handler`);
    this.__local_emitter.emit(this.__message_event, data);
  }

  attach(supportedEvent:string, params:string) {
    // attach supported event and emit data to
    console.log(`FROM type ${PluginEnum.blockchain} - attaching event ${supportedEvent}`);
    console.log("parameters passed are: ", params)
    setInterval(() => {
      this.emit(this.structureData({
        containerId: "", 
        data: {
          color: {
	 	background: "red",
	        border: "red"	
	  },
	  borderWidth: 1,
	  shape: "triangle"
        },
      }));
    }, 1000);
  }


  detach(supportedEvent:string) {
	console.log(`About to detach event ${supportedEvent}`)
  }

  structureData(data:any) {
    return {
      eventType: event_type.data,
      timestamp: Date.now(),
      containerId: data.containerId,
      data: data.data,
    };
  }
}

export default BlockchainPlugin;
