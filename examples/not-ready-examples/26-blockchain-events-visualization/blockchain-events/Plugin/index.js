const Plugin = require('./Plugin');
const PluginEnum = require('./PluginEnum');

const plugin = new Plugin(PluginEnum.blockchain);

plugin.onMessage((data) => {
  console.log(JSON.parse(data))
});

plugin.run();
plugin.attach('pendingTransactions')
// plugin.detach('pendingTransaction')
