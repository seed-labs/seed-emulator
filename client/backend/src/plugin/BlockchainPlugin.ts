import Web3 from 'web3'
import EventEmitter from './EventEmitter';
import PluginEnum from './PluginEnum';
import PluginInterface from './PluginInterface';
import { SeedContainerInfo } from '../utils/seedemu-meta';
//import DockerOdeWrapper from './DockerOdeWrapper'

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
  private __accountsToContainerMap:  {[key: string]: string};
  private __containers: SeedContainerInfo[];
  private __settings: {
    filters: string[];
  };
  
  constructor(containers?:SeedContainerInfo[]) {
    this.__message_event = `message:${PluginEnum.blockchain}`;
    this.__local_emitter = EventEmitter.emitters[PluginEnum.blockchain];
    this.__settings = settings;
    this.__accountsToContainerMap = {};
    this.__containers = this.__setContainers(containers);
    this.__driver()
  }

  async __driver() {
    this.emit({
      eventType: event_type.settings,
      data: this.__settings,
    });  
  }

  __setContainers(containers:SeedContainerInfo[] = []) {
	const c = containers.filter(container => container.Names[0].includes('Ethereum'))
  	return c
  }

  emit(data:object) {
    console.log(`FROM type ${PluginEnum.blockchain} - emitting data ${JSON.stringify(data)} to main handler`);
    this.__local_emitter.emit(this.__message_event, data);
  }

  attach(supportedEvent:string, params:string) {
    // attach supported event and emit data to
    console.log(`FROM type ${PluginEnum.blockchain} - attaching event ${supportedEvent}`);
    setInterval(() => {
      this.emit(this.structureData({
        containerId: "", 
        data: {
          color: {
	 	background: "red",
	        border: "red"	
	  },
	  size: 80,
	  borderWidth: 5,
	  shape: "triangle"
        },
      }));
    }, 1000);
  }


  detach(supportedEvent:string) {
	console.log(`About to detach event ${supportedEvent}`)
  	// unsubscribe using web3
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
