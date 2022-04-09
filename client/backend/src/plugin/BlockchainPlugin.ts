import Web3 from 'web3'
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

const visualize = {
  pendingTransaction:{
    color: {
      background: "orange",
      border: "orange"	
     },
     borderWidth: 2,
    //  size: 80,
    //  shape: "triangle"
  },
  newBlockHeaders: {
    color: {
      background: "purple",
      border: "purple"	
     },
     borderWidth: 2,
  }
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

  __driver() {
    this.emit({
      eventType: event_type.settings,
      data: this.__settings,
      status: status.success
    });  

    this.__containers.map((container, index) => {
      const split = container.Names[0].split("-");
      const ip = split[split.length - 1];
      const web3 = new Web3(`ws://${ip}:8546`);
      if (index === 0) {
        this.__web3 = web3;
      }
      return (web3.eth.getAccounts())
        .then((accounts:string[]) => {
          // console.log(`${ip}-seedemu-accounts: `, accounts)
          accounts.forEach(account => {
            this.__accountsToContainerMap[account.toLowerCase()] = container.Id;
          });
      })
    })
    
    setTimeout(() => {
      console.log(this.__accountsToContainerMap)
    },3000)
  }

  __setContainers(containers:SeedContainerInfo[] = []) {
	const c = containers.filter(container => container.Names[0].includes('miner'))
  	return c
  }

  emit(data:object) {
    console.log(`FROM type ${PluginEnum.blockchain} - emitting data ${JSON.stringify(data)} to main handler`);
    this.__local_emitter.emit(this.__message_event, data);
  }

  attach(supportedEvent:string, params:string) {
    // attach supported event and emit data to
    console.log(`FROM type ${PluginEnum.blockchain} - attaching event ${supportedEvent}`);
    this.__web3.eth.subscribe(supportedEvent, (error:any, result:any) => {
      if(error || !Array.isArray(result)){
        this.emit({
          status: status.error,
          error
        })
        return;
      }
      const {from, to, contract} = handleSubscriptionResults(this.__web3, supportedEvent, result);
      const containerId = this.__accountsToContainerMap[from];
      
      const data = visualize[supportedEvent];
      if(supportedEvent === subscriptions.pendingTransactions && contract) {
        data.color.background = 'pink'
        data.color.border = 'pink'
      }

      this.emit(this.structureData({
        status: status.success,
        containerId,
        data
      }))
    })
  }


  detach(supportedEvent:string) {
	  console.log(`About to detach event ${supportedEvent}`)
  	// unsubscribe using web3
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


function handleSubscriptionResults(web3:Web3, subscription:string, result:any) {
	if(subscription === subscriptions.newBlockHeaders) {
      return {
        from: result.miner.toLowerCase()
      } 
  } else if (subscription === subscriptions.pendingTransactions) {
      return getTransactionReceipt(web3, result)
  }
}

function getTransactionReceipt(web3: Web3, transactionHash:string) {
	web3.eth.getTransactionReceipt(transactionHash, (error:any, receipt:any) => {
		if(receipt !== null) {
      return {
        from: receipt.from.toLowerCase(),
        to: receipt.to ? receipt.to.toLowerCase() : '',
        contract: receipt.contractAddress
      }
		} else {
			setTimeout(() => {
				getTransactionReceipt(web3, transactionHash)
			},1000)
		}
	})
}

export default BlockchainPlugin;
