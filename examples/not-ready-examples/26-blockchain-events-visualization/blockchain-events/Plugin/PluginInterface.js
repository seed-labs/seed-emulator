class PluginInterface {
  constructor() {
    if (!this.emit || typeof this.emit !== 'function') {
      throw new Error('Plugin must implement the emit function!');
    }
    if (!this.attach || typeof this.attach !== 'function') {
      throw new Error('Plugin must implement the attach function!');
    }
    /*
    if (!this.detach || typeof this.detach !== 'function') {
      throw new Error('Plugin must implement the detach function!');
    }	
    */
    if (!this.structureData || typeof this.attach !== 'function') {
      throw new Error('Plugin must implement the structureData function!');
    }
  }
}

module.exports = PluginInterface;
