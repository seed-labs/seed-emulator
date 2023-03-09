window.onload = function () {
  init();
};

var total_blocks_shown = 20;
var total_transactions_shown = 50;
var provider_url = emulator_parameters["web3_provider"];
var waiting_time = parseInt(emulator_parameters["client_waiting_time"]);
var providers = [];
var most_recent_block = 0;
var init_block = 0;
var BLOCK_URL = "/block/";
var TX_URL = "/tx/";

async function init() {
  // get all the current addresses from the server
  //get_web3_providers('/get_web3_providers');
  update_view();
  await set_navigator();

  window.setInterval(update_view, waiting_time * 1000);
  window.setInterval(update_timestamp, 1000);
  document.getElementById("defaultOpen").click();

  let button = document.getElementById("new-block-button");
  button.setAttribute("onclick", "show_new_block()");
}
async function show_new_block() {
  let number = document.getElementById("new-block-number").value;
  show_block(number);
}
async function show_block(block_number) {
  var provider = ethers.getDefaultProvider(provider_url);
  var block = await provider.getBlockWithTransactions(parseInt(block_number));

  let page_title = document.getElementById("page-title");
  page_title.innerHTML = "Block #" + block_number;

  let block_table = document.getElementById("block-table-body");
  block_table.innerHTML = ""; // Clear the table

  for (var key in block) {
    let table_row = document.createElement("tr");
    table_row.setAttribute("id", key);

    if (key === "transactions") {
      transactions = block.transactions;
      if (transactions.length > 0) {
        var content = "";
        console.log(transactions);
        for (let i = 0; i < transactions.length; i++) {
          var trx = transactions[i];
          content += `<a href="/tx/${trx.hash}">${trx.hash}</a><br>`;
        }
      } else {
        content = "No transaction";
      }
      table_row.innerHTML = `
              <td>${key}</td> 
          <td>${content}</td>`;
    } else {
      table_row.innerHTML = `
              <td>${key}</td> 
                  <td>${block[key]}</td>`;
    }
    block_table.append(table_row);
  }
}
async function get_web3_providers(url) {
  const response = await fetch(url);

  providers = await response.json();
  console.log(providers);
  if (response) {
    set_provider_selector();
  }
}

async function get_blocks() {
  var blocks = [];
  var provider = ethers.getDefaultProvider(provider_url);
  var latest_block_number = await provider.getBlockNumber();

  if (latest_block_number <= most_recent_block) return;

  if (latest_block_number - most_recent_block > total_blocks_shown) {
    if (most_recent_block == 0) {
      init_block = latest_block_number - total_blocks_shown;
    }
    most_recent_block = latest_block_number - total_blocks_shown;
  }

  let block_area = document.getElementById("block-list");
  for (let i = most_recent_block + 1; i <= latest_block_number; i++) {
    var block = await provider.getBlockWithTransactions(i);
    blocks.push(block);
  }
  most_recent_block = latest_block_number;
  return blocks;
}
async function update_timestamp() {
  for (let i = init_block; i <= most_recent_block; i++) {
    let timestamp = document.getElementById(`${i}_timestamp`);
    if (timestamp) {
      timestamp = parseInt(timestamp.innerText);
    }

    let sec = Math.floor((Date.now() - timestamp * 1000) / 1000);
    let time = `<a hidden id=${i}_timestamp> ${timestamp}</a>`;
    if (sec < 60) {
      time += `${sec} seconds ago`;
    } else {
      let min = Math.floor(sec / 60);
      if (min == 1) {
        time += `${Math.floor(sec / 60)} min ago`;
      } else {
        time += `${Math.floor(sec / 60)} mins ago`;
      }
    }
    $("#" + i.toString() + "_time").html(time);
  }
}
async function update_view() {
  var blocks = await get_blocks();
  if (blocks) {
    show_blocks(blocks);
    show_block_history(blocks);
  }
}
async function show_block_history(blocks) {
  for (let i = 0; i < blocks.length; i++) {
    var block = blocks[i];
    var url = BLOCK_URL + block.number;
    block.block_number = `<a href=${url}>${block.number}</a>`;
    block.txn = block.transactions.length;
    block.reward = ethers.BigNumber.from(0);
    block.time = `<a hidden id=${block.number}_timestamp> ${block.timestamp}</a>`;
    block.burntFee = block.baseFeePerGas.mul(block.gasUsed);
    block.baseFeePerGas = ethers.utils.formatUnits(block.baseFeePerGas, "gwei");
    block.gasUsed = block.gasUsed.toString();
    block.gasLimit = block.gasLimit.toString();
    var sec = Math.floor((Date.now() - block.timestamp * 1000) / 1000);
    if (sec < 60) {
      block.time += `${sec} seconds ago`;
    } else {
      let min = Math.floor(sec / 60);
      if (min == 1) {
        block.time += `${Math.floor(sec / 60)} min ago`;
      } else {
        block.time += `${Math.floor(sec / 60)} mins ago`;
      }
    }
    for (let j = 0; j < block.txn; j++) {
      var provider = ethers.getDefaultProvider(provider_url);
      var hash = block.transactions[j].hash;
      var tx = await provider.getTransaction(hash);
      var tx_r = await provider.getTransactionReceipt(hash);
      gasPrice = ethers.utils.formatUnits(tx.gasPrice, "gwei");
      gasUsed = tx_r.gasUsed.toString();
      block.reward = block.reward.add(tx.gasPrice.mul(tx_r.gasUsed));
    }
    block.reward =
      ethers.utils.formatUnits(block.reward.sub(block.burntFee), "ether") +
      " Ether";
    block.burntFee = ethers.utils.formatUnits(block.burntFee, "ether");
    insertTable(
      "blocks-table-body",
      [
        "block_number",
        "time",
        "txn",
        "miner",
        "gasUsed",
        "gasLimit",
        "baseFeePerGas",
        "reward",
        "burntFee",
      ],
      block
    );
  }
}
async function show_blocks(blocks) {
  let block_area = document.getElementById("block-list");

  for (let i = 0; i < blocks.length; i++) {
    var block = blocks[i];

    var node = document.getElementById("block-" + block.number);
    if (node != null) continue; // the node already exists

    node = document.createElement("li");
    number_of_tx = block.transactions.length;
    node.setAttribute("class", "list-group-item");
    node.setAttribute("id", "block-" + block.number);

    var url = BLOCK_URL + block.number;
    text =
      `<a href="${url}">${block.number}</a>: &nbsp;` +
      get_short_hash(block.hash) +
      `&nbsp;(${number_of_tx})`;

    node.innerHTML = text;

    // Insert the node at the top, and remove one the bottom if needed
    block_area.insertBefore(node, block_area.firstChild);
    while (block_area.childElementCount > total_blocks_shown) {
      block_area.removeChild(block_area.lastChild);
    }

    // Display transactions
    show_transactions(block.number, block.transactions);
  }
}

function show_transactions(block_number, transactions) {
  length = transactions.length;
  let tx_area = document.getElementById("transaction-list");
  for (i = 0; i < length; i++) {
    var node = document.createElement("li");
    var tx = transactions[i];
    node.setAttribute("class", "list-group-item");
    node.setAttribute("id", "tx-" + tx.hash);
    addr_from = get_short_number(tx.from, 5, 2);
    addr_to = get_short_number(tx.to, 5, 2);
    url = TX_URL + tx.hash;
    text =
      `${block_number}: &nbsp;` +
      `<a href="${url}">${get_short_number(tx.hash, 6, 4)}</a>` +
      ` (${addr_from} --> ${addr_to})`;
    node.innerHTML = text;

    tx_area.insertBefore(node, tx_area.firstChild);
    while (tx_area.childElementCount > total_transactions_shown) {
      tx_area.removeChild(tx_area.lastChild);
    }
  }
}

function copy_to_clipboard(value) {
  // Copy the text inside the text field
  navigator.clipboard.writeText(value);

  console.log("Copied the text: " + value);
}

function get_short_hash(hash) {
  short_hash = hash.slice(0, 8) + "..." + hash.slice(35, 41);
  return short_hash;
}

function get_short_number(number, from_start, from_end) {
  if (number == null) {
    return "null";
  }
  end = number.length;
  short_number =
    number.slice(0, from_start) +
    "..." +
    number.slice(end - from_end - 1, end - 1);
  return short_number;
}

function insertTable(tableId, fields, data) {
  let tableRef = document.getElementById(tableId);
  let newRow = tableRef.insertRow(0);
  $.each(fields, function (index, field) {
    let newCell = newRow.insertCell(index);
    newCell.id = data["number"] + "_" + field;

    let newText = document.createTextNode("");
    if (data[field] != null) {
      newText = document.createTextNode(
        JSON.stringify(data[field]).replaceAll('"', "")
      );
    }
    $("#" + data["number"] + "_" + field).html(data[field]);
  });
}
