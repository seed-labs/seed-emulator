window.onload = function () {
  init();
};

var provider_url = emulator_parameters["web3_provider"];
var waiting_time = parseInt(emulator_parameters["client_waiting_time"]);
var accounts;
var providers;

async function init() {
  // get all the current addresses from the server
  accounts = await get_accounts("/get_accounts");
  if (accounts != null) show_accounts(accounts);

  providers = await get_web3_providers("/get_web3_providers");
  if (providers != null) set_provider_selector();
  await set_navigator();
  update_balance();

  window.setInterval(update_balance, waiting_time * 1000);
}

async function get_accounts(url) {
  const response = await fetch(url);

  all_accounts = await response.json();
  if (response) {
    // Sort by type and then name: "local" type goes before "emulator" type.
    all_accounts.sort(function (a, b) {
      if (a.type === b.type) {
        // Price is only important when cities are the same
        return a.name > b.name ? 1 : -1;
      }
      return a.type < b.type ? 1 : -1;
    });

    return all_accounts;
  } else {
    return null;
  }
}

async function get_web3_providers(url) {
  const response = await fetch(url);

  all_providers = await response.json();
  if (response) {
    return all_providers.sort();
  } else {
    return null;
  }
}

// Display accounts (balance is set to empty)
function show_accounts(data) {
  if (accounts == null) return;

  let table_body = document.getElementById("table-body");

  for (let r of data) {
    short_address = get_short_address(r.address);
    let table_row = document.createElement("tr");
    table_row.setAttribute("id", r.address);
    table_row.innerHTML = `
             <td>${short_address}</td>
             <td>${r.name}</td>
             <td></td>
             <td></td>
             <td></td>`;
    table_body.append(table_row);
  }
}

// Update each row of the table, updating balance and change
async function update_balance() {
  // sort the data by address
  var data = accounts;

  if (data == null) return;

  console.log("show_balance() is invoked");

  for (let r of data) {
    let balance = await get_balance(r.address);
    let nonce = await get_nonce(r.address);
    let change = 0;
    let color = "black";

    if ("balance" in r) {
      change = balance - r["balance"];
      if (change == 0) {
        // If change == 0, keep the previous change
        change = r["recent-change"];
      } else r["recent-change"] = change;

      r["balance"] = balance;
    } else {
      r["balance"] = balance;
      r["recent-change"] = 0;
    }

    short_address = get_short_address(r.address);
    if (change > 0) color = "green";
    else if (change < 0) color = "red";
    else color = "black";

    let table_row = document.getElementById(r.address);
    table_row.innerHTML = `
             <td>${short_address}</td>
             <td>${r.name}</td>
             <td>${balance}</td>
             <td><font color="${color}">${change}</font></td>
             <td>${nonce}</td>`;
    //    <td onclick="copy_to_clipboard(\'${r.address}\')">${short_address}
    //             <i class="fa fa-files-o" aria-hidden="true"></i></td>
  }
}

function copy_to_clipboard(address) {
  // Copy the text inside the text field
  navigator.clipboard.writeText(address);

  console.log("Copied the text: " + address);
}

async function get_balance(address) {
  var provider = ethers.getDefaultProvider(provider_url);
  var balance = await provider.getBalance(address);

  //console.log(address + ':' + ethers.utils.formatEther(balance));
  eth_balance = ethers.utils.formatEther(balance, { commify: true });
  eth_balance = (+eth_balance).toPrecision(10);
  return eth_balance;
}

async function get_nonce(address) {
  var provider = ethers.getDefaultProvider(provider_url);
  var nonce = await provider.getTransactionCount(address, 'pending');

  return nonce;
}

function get_short_address(address) {
  short_address = address.slice(0, 8) + "..." + address.slice(35, 41);
  return short_address;
}

function set_provider_selector() {
  let provider_selector = document.getElementById("provider-selector");


    let options = `<option selected>${provider_url}</option>`;
    for (let p of providers) {
        options += `<option value="${p}">${p}</option>`
    }


  provider_selector.innerHTML = options;
  provider_selector.onchange = function () {
    provider_url = this.value;
  };
}
