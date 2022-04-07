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
   
    
   //const web3_eth1 = new Web3(new Web3.providers.WebsocketProvider(`ws://${ip}:8546`));
    
    //const web3_eth2 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8545"));
    //const web3_eth3 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8546"));
    //const web3_eth4 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8547"));
    //const web3_eth5 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8548"));
    //const web3_eth6 = new Web3(new Web3.providers.WebsocketProvider("ws://localhost:8549"));
	
    //const eth1_accounts = await web3_eth1.eth.getAccounts()
    //console.log(eth1_accounts)
    /*
    const eth2_accounts = await web3_eth2.eth.getAccounts()
    const eth3_accounts = await web3_eth3.eth.getAccounts()
    const eth4_accounts = await web3_eth4.eth.getAccounts()
    const eth5_accounts = await web3_eth5.eth.getAccounts()
    const eth6_accounts = await web3_eth6.eth.getAccounts()
	
    const totalNumberOfAccounts = eth1_accounts.length + eth2_accounts.length + eth3_accounts.length + eth4_accounts.length + eth5_accounts.length + eth6_accounts.length;

    eth1_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
    eth2_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
    eth3_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
    eth4_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
    eth5_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
    eth6_accounts.forEach(account => this.__accountsToContainerMap[account.toLowerCase()] = '')
	console.log(this.__accountsToContainerMap)
    let matchingAccounts = 0;

    this.__containers.forEach(async (container) =>{
             const c = await DockerOdeWrapper.docker.getContainer(docker, container.Id)
             const output = await DockerOdeWrapper.container.exec(docker, c, 'geth attach --exec eth.accounts')
             const accounts = JSON.parse(output)
             accounts.forEach((account) => {
                     if(accountsToContainerMap.hasOwnProperty(account)) {
                             matchingAccounts++
     			     accountsToContainerMap[account] = container.Id
                     }
             })
     })
     setTimeout(() => {
       console.log(this.__accountsToContainerMap)
     }, 3000)
*/
  }

  __setContainers(containers:SeedContainerInfo[] = []) {
	const c = containers.filter(container => container.Names[0].includes('Ethereum'))
  	console.log(c.length)
  	return c
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
	  size: 80,
	  borderWidth: 5,
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
