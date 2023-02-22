var provider_url = emulator_parameters["web3_provider"];
var block_number = emulator_parameters["block_number"];

window.onload = function () {
  let button = document.getElementById("new-block-button");
  button.setAttribute("onclick", "show_new_block()");
  set_navigator();
  show_block(block_number);
};

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
