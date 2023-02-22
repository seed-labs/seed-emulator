window.onload = function () {
  init();
};

async function init() {
  providers = await get_beacon_providers();
  if (providers != null) {
    set_provider_selector();
  }
  // Get the element with id="defaultOpen" and click on it
  document.getElementById("defaultOpen").click();

  update_current_slot();
  initOverview();
  window.setInterval(update_current_slot, 10000);
}

var slot_fields = [
  "epoch",
  "slot",
  "block_number",
  "recipient",
  "status",
  "timestamp",
  "proposer",
  "parent_root",
  "state_root",
  "signature",
  "randao_reveal",
  "eth_data",
  "execution_payload",
  "attestations",
  "deposits",
];

async function initOverview() {
  let res = await request_api(
    provider_url + "/eth/v2/beacon/blocks/" + slot_number
  );
  res = res.data;
  let slot_details = {};
  slot_details.slot = res.message.slot;
  slot_details.epoch = Math.floor(parseInt(res.message.slot) / 4);
  slot_details.block_number = res.message.body.execution_payload.block_number;
  slot_details.recipient = res.message.body.execution_payload.fee_recipient;
  slot_details.timestamp = new Date(
    parseInt(res.message.body.execution_payload.timestamp) * 1000
  );
  slot_details.proposer = res.message.proposer_index;
  slot_details.parent_root = res.message.parent_root;
  slot_details.state_root = res.message.state_root;
  slot_details.randao_reveal = res.message.body.randao_reveal;
  slot_details.signature = res.signature;
  slot_details.eth_data = res.message.body.eth1_data;
  slot_details.execution_payload = res.message.body.execution_payload;
  slot_details.attestations = res.message.body.attestations.length;
  slot_details.deposits = res.message.body.deposits.length;
  slot_details.status = `<span class="badge badge-pill bg-success text-white">Proposed</span>`;

  let attestations = [];
  $.each(res.message.body.attestations, function (index, attestation) {
    attestation.aggregation_bits = parseInt(
      attestation.aggregation_bits.replace("0x", ""),
      16
    ).toString(2);
    attestation = { ...attestation, ...attestation.data };
    attestation.source = attestation.data.source.epoch;
    attestation.target = attestation.data.target.epoch;
    attestations.push(attestation);
  });

  res = await request_api(
    provider_url + "/eth/v1/beacon/states/head/finality_checkpoints"
  );
  finalized_epoch = parseInt(res["data"]["finalized"]["epoch"]);
  if (parseInt(slot_details.epoch) <= finalized_epoch) {
    slot_details.status += `<span class="badge badge-pill bg-success text-white">Finalized</span>`;
  }
  loadSlotDetails(slot_fields, slot_details);
  loadAttestations(attestations);
  loadTransactions(slot_details.block_number);
}

async function loadTransactions(block_number) {
  let provider = ethers.getDefaultProvider(
    provider_url.replace("8000", "8545")
  );
  let block = await provider.getBlock(parseInt(block_number));

  fields = ["hash", "from", "to", "value"];
  let divs = `<div class="card my-2">`;

  for (let i = 0; i < block.transactions.length; i++) {
    let tx = await provider.getTransaction(block.transactions[i]);
    divs += `<div class="card-body px-0 py-1">
                    <div class="row border-bottom p-1 mx-0">
                        <div class="col-md-12 text-center">Transaction ${i}</div>
                    </div>`;
    $.each(fields, function (index, field) {
      if (field == "hash") {
        divs += `<div class="row border-bottom p-1 mx-0">
                        <div class="col-md-2"> ${field}:</div>
                        <div class="col-md-10"><a href="/tx/${tx[field]}">${tx[field]}</a></div>
                    </div>`;
      } else {
        divs += `<div class="row border-bottom p-1 mx-0">
                            <div class="col-md-2"> ${field}:</div>
                            <div class="col-md-10">${tx[field]}</div>
                        </div>`;
      }
    });
    divs += `</div>`;
  }
  if (block.transactions.length == 0) {
    divs += `<div class="card-body px-0 py-1">
                    <div class="row border-bottom p-1 mx-0">
                        <div class="col-md-12 text-center">No Transaction</div>
                    </div>
                </div>`;
  }
  divs += `</div>`;
  $("#Transactions").html(divs);
}

// async function loadTransactions(block_number){
//     let provider = ethers.getDefaultProvider(provider_url.replace("8000", "8545"));
//     let block = await provider.getBlock(parseInt(block_number));
//     let tx_list = [];
//     var tbody = "";
//     for (let i=0; i< block.transactions.length; i++){
//         let tx = await provider.getTransaction(block.transactions[i]);
//         tbody += `<tr>
//                     <td>${tx.hash}</td>
//                     <td>${tx.from}</td>
//                     <td>${tx.to}</td>
//                     <td>${tx.value}</td>
//                 </tr>`
//     }

//     console.log(tbody)
//     $("#table-body").html(tbody);
// }

async function loadAttestations(data) {
  fields = [
    "slot",
    "index",
    "aggregation_bits",
    "beacon_block_root",
    "source",
    "target",
    "signature",
  ];
  let divs = `<div class="card my-2">`;

  $.each(data, function (index, aggregation) {
    divs += `<div class="card-body px-0 py-1">
                    <div class="row border-bottom p-1 mx-0">
                        <div class="col-md-12 text-center">Attestation ${index}</div>
                    </div>`;
    $.each(fields, function (index, field) {
      divs += `<div class="row border-bottom p-1 mx-0">
                        <div class="col-md-2"> ${field}:</div>
                        <div class="col-md-10">${aggregation[field]}</div>
                    </div>`;
    });
    divs += `</div>`;
  });
  divs += `</div>`;
  $("#Attestations").html(divs);
}
async function loadSlotDetails(fields, data) {
  let divs = "";
  $.each(fields, function (index, field) {
    let div = "<div class='row border-bottom p-3 mx-0'>";
    div += "<div class='col-md-2'>" + field + " :</div>";
    let content = data[field];
    if (typeof content === "object") {
      content = JSON.stringify(content, null, 3);
    }
    div += "<div class='col-md-10'>" + content + "</div>";
    div += "</div>";
    divs += div;
  });
  $("#Overview").html(divs);
}
