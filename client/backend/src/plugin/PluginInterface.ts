import { SeedContainerInfo } from '../utils/seedemu-meta';

interface PluginInterface {
  getMessageEvent():string;
  getLocalEmitter():any;
  getContainers():SeedContainerInfo[];
  getSettings():{filters: string[]}
  emit: (data:object) => void;
  attach:(event:string, params:string) => void;
  detach:(event:string) => void;
  structureData:(data: object) =>void;
}

export default PluginInterface;
