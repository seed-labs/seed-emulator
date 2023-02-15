var provider_url = emulator_parameters["web3_provider"];
var tx_hash = emulator_parameters["tx_hash"];

window.onload = function () {
  show_tx(tx_hash);

  let button = document.getElementById("new-tx-button");
  button.setAttribute("onclick", "show_new_tx()");

  // Show the default tab
  document.getElementById("defaultOpen").click();
};

async function show_new_tx() {
  let hash = document.getElementById("new-tx-hash").value;
  show_tx(hash);
}

async function show_tx(hash) {
  var provider = ethers.getDefaultProvider(provider_url);
  var tx = await provider.getTransaction(hash);

  if ("wait" in tx) {
    tx["wait"] = "(omitted)";
  }
  add_to_page(tx, "tx-table-body");

  var tx_r = await provider.getTransactionReceipt(hash);
  if ("logsBloom" in tx_r) {
    tx_r["logsBloom"] = "(omitted)";
  }
  add_to_page(tx_r, "tx-receipt-table-body");
}

function add_to_page(content, element_id) {
  let table = document.getElementById(element_id);
  table.innerHTML = ""; // Clean the table first
  for (var key in content) {
    let row = document.createElement("tr");
    row.setAttribute("id", key);
    row.innerHTML = `
	        <td>${key}</td> 
                <td>${content[key]}</td>`;
    table.append(row);
  }
}
