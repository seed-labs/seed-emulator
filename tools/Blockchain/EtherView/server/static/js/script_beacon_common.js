var providers;
var provider_url;

function loadTable(tableId, fields, data) {
  var rows = "";
  $.each(data, function (index, item) {
    var row = "<tr>";
    $.each(fields, function (index, field) {
      let cellText = "";
      if (item[field] != null) { 
        cellText = JSON.stringify(item[field]);
      }

      row += "<td id=" + item['slot_number']+ "_" + field + ">" + cellText.replaceAll('"', '') + "</td>";

    });
    rows += row + "</tr>";
  });
  $("#" + tableId).html(rows);
}

function insertTable(tableId, fields, data){
  let tableRef = document.getElementById(tableId);
  let newRow = tableRef.insertRow(0);
  $.each(fields, function (index, field) {
    let newCell = newRow.insertCell(index);
    newCell.id = data['slot']+ "_" + field;

    let newText = document.createTextNode("");
    if (data[field] != null) { 
      newText = document.createTextNode(JSON.stringify(data[field]).replaceAll('"', ''));
    }
    newCell.appendChild(newText);
  });
}

async function update_current_slot() {
  const current_slot = document.getElementById("current_slot");
  const current_epoch = document.getElementById("current_epoch");

  cur_slot = await get_current_slot();

  current_slot.innerHTML = "Current Slot: " + cur_slot;
  current_epoch.innerHTML =
    "Current Epoch: " + Math.floor(parseInt(cur_slot) / 4);
}

async function get_current_slot() {
  response = await request_api(provider_url + "/eth/v1/beacon/headers");

  return parseInt(response["data"][0]["header"]["message"]["slot"]);
}

async function get_beacon_providers() {
  all_providers = await request_api("/get_beacon_providers");
  return all_providers.sort();
}

function set_provider_selector() {
  let provider_selector = document.getElementById("provider-selector");
  let options = ``;
  providers.forEach(function (p, index) {
    if (index == 5) {
      provider_url = p;
      options = `<option selected>Provider: ${p}</option>`;
    }
    options += `<option value="${p}">Provider: ${p}</option>`;
  });

  provider_selector.innerHTML = options;
  provider_selector.onchange = function () {
    provider_url = this.value;
  };
}

async function request_api(url) {
  const response = await fetch(url);

  res = await response.json();

  if (response) {
    return res;
  } else {
    return null;
  }
}
