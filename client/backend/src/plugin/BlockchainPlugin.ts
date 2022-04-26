import Web3 from 'web3'
import axios from 'axios'
import EventEmitter from './EventEmitter';
import PluginEnum from './PluginEnum';
import PluginInterface from './PluginInterface';
import { SeedContainerInfo } from '../utils/seedemu-meta';

const subscriptions = {
  pendingTransactions: 'pendingTransactions',
  newBlockHeaders: 'newBlockHeaders'
}

const status = {
  success: 'success',
  error: 'error'
}

const event_type = {
  settings: 'settings',
  data: 'data',
};

const settings = {
  filters: [subscriptions.newBlockHeaders, subscriptions.pendingTransactions],
};

// need to create an interface for all plugins to follow this one
class BlockchainPlugin implements PluginInterface {
  private __message_event: string;
  private __local_emitter: any;
  private __accountsToContainerMap:  {[key: string]: string};
  private __containers: SeedContainerInfo[];
  private __http_url: string;
  private __websocket_url: string;
  private __settings: {
    filters: string[];
  };
  private __web3: Web3;
  
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
      status: status.success
    });  

    this.__containers.map((container, index) => {
      const split = container.Names[0].split("-");
      const ip = split[split.length - 1];
      this.__http_url = `http://${ip}:8545`
      this.__websocket_url = `ws://${ip}:8546`    
      const web3 = new Web3(new Web3.providers.WebsocketProvider(this.__websocket_url, {
      	clientConfig: {
      		// Useful to keep a connection alive
      		keepalive: true,
      		keepaliveInterval: 60000 // ms
    	},
      }));
      if (!this.__web3) {
        this.__web3 = web3;
      }
      return (web3.eth.getAccounts())
        .then((accounts:string[]) => {
          accounts.forEach(account => {
            this.__accountsToContainerMap[account.toLowerCase()] = container.Id;
          });
      })
    })

    setTimeout(() => {
      console.log(this.__accountsToContainerMap)
    },3000)
  }

  getMessageEvent():string {
  	return this.__message_event;
  }

  getLocalEmitter():any {
 	return this.__local_emitter;
  }

  getSettings():  {  filters: string[];  } {
 	return this.__settings; 
  }

  getContainers(): SeedContainerInfo[] {
  	return this.__containers;
  }

  __setContainers(containers:SeedContainerInfo[] = []) {
	return containers.filter(container => container.Names[0].includes('Ethereum'))
  }

  emit(data:object) {
    console.log(`FROM type ${PluginEnum.blockchain} - emitting data ${JSON.stringify(data)} to main handler`);
    this.__local_emitter.emit(this.__message_event, data);
  }

  attach(supportedEvent: any, params: string) {
	console.log(`FROM type ${PluginEnum.blockchain} - attaching event ${supportedEvent}`);
  	const subscription = this.__web3.eth.subscribe(supportedEvent, (error: any, result:any) => {
		if(error) {
			this.emit({
				status: status.error,
				error
			})
			return;
		}
		this.__handleSubscriptionResults(supportedEvent, result);
	})
	this.__local_emitter.on(`detach:${PluginEnum.blockchain}:${supportedEvent}`, () => {
		subscription.unsubscribe(function(error, success){
    			if(success)
        			console.log('Successfully unsubscribed!');
		});
	})
  }
  async __handleSubscriptionResults(supportedEvent:any, result:any) {
  	
        if(supportedEvent === subscriptions.newBlockHeaders) {
	       this.emit(this.structureData({
	       		status: status.success,
			containerId: await this.__getContainerId(result.miner, result.number),
			data: {
				borderWidth: 4,
				color: {
					background: "purple",
					border: "purple"
				}
			}
	       }))	
  	} else if (supportedEvent === subscriptions.pendingTransactions) {
      		this.__getTransactionReceipt(result)
  	}
  }

  async __getContainerId(address:string, blockNumber:number) {
	const addr = address.toLowerCase() 
	const self = this;
	return new Promise((resolve, reject) => {
		if(self.__accountsToContainerMap[addr]) {
			return resolve(self.__accountsToContainerMap[addr])
		} else {
			return axios.post(this.__http_url, {
				jsonrpc: '2.0',
				id: Date.now(),
				method: 'clique_getSnapshot',
				params: [self.__web3.utils.toHex(blockNumber)]
			}, {
				headers: {
					'Content-Type': 'application/json',
					'Access-Control-Allow-Origin': '*'
				}
			}).then(function(result) {
				return resolve(self.__accountsToContainerMap[result.data.result.recents[blockNumber]])
			}).catch(function(e) {
				return reject(e)
			})
		}
	})
  }

  __getTransactionReceipt(transactionHash: any) {
	const self = this;
  	this.__web3.eth.getTransactionReceipt(transactionHash, async (error:any, receipt:any) => {
		if(receipt !== null) {
			this.emit(this.structureData({
                        	status: status.success,
                        	containerId: await self.__getContainerId(receipt.from, receipt.number),
                        	data: {
                                	borderWidth: 4,
                                	color: {
                                        	background: !!receipt.contractAddress ? "pink" : "orange",
                                        	border: !!receipt.contractAddress ? "pink" : "orange"
                                	}
                        	}
               		}))
		} else {
			setTimeout(() => {
				this.__getTransactionReceipt(transactionHash)
			},1000)
		}
	})
  }

  detach(supportedEvent:any) {
  	console.log(`About to detach event ${supportedEvent}`)
  	// unsubscribe using web3
  	this.__local_emitter.emit(`detach:${PluginEnum.blockchain}:${supportedEvent}`)
  }

  structureData(data:any) {
    return {
      eventType: event_type.data,
      timestamp: Date.now(),
      status: data.status,
      containerId: data.containerId,
      data: data.data,
    };
  }
}

export default BlockchainPlugin;