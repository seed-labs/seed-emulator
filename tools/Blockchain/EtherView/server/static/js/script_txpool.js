window.onload = function () {
  init();
};

var provider_urls;
var providers = [];
async function init() {
  provider_urls = await get_web3_providers("/get_web3_providers");
  for (let i = 0; i < provider_urls.length; i++) {
    var provider = {};
    provider.url = provider_urls[i];
    providers.push(provider);
  }
  await set_navigator();
  await update_txpool();

  window.setInterval(update_txpool, 3 * 1000);
}

async function update_txpool() {
  for (let i = 0; i < providers.length; i++) {
    var provider = new ethers.providers.JsonRpcProvider(provider_urls[i]);
    var txpool_length = 0;

    if (provider) {
      txpool = await provider.send("txpool_inspect");

      if (txpool) {
        addrs = Object.keys(txpool.pending);
        for (let j = 0; j < addrs.length; j++) {
          nonce_list = Object.keys(txpool.pending[addrs[j]]);
          txpool_length += nonce_list.length;
        }
      }
    }
    providers[i].txpool = txpool_length;
  }
  loadTable("txpool-table-body", ["url", "txpool"], providers);
}

function loadTable(tableId, fields, data) {
  var rows = "";
  $.each(data, function (index, item) {
    var row = "<tr>";
    $.each(fields, function (index, field) {
      let cellText = "";
      if (item[field] != null) {
        cellText = item[field];
      }

      row += "<td>" + cellText + "</td>";
    });
    rows += row + "</tr>";
  });
  $("#" + tableId).html(rows);
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
