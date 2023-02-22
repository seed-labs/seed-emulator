window.onload = function () {
  init();
};

var current_epoch = null;
var initial_epoch = null;
var current_slot = null;
var slot_info = [];

async function init() {
  providers = await get_beacon_providers();
  if (providers != null) {
    set_provider_selector();
  }
  await set_navigator();

  update_current_slot();
  init_slot();




  window.setInterval(update_current_slot, 10000);
  window.setInterval(update_slot, 10000);
  window.setInterval(update_timestamp, 1000);
}

async function init_slot() {
  current_slot = await get_current_slot();
  updated_epoch = Math.floor(parseInt(current_slot) / 4);

  current_epoch = updated_epoch - 2;
  initial_epoch = current_epoch;

  for (let epoch = current_epoch; epoch <= updated_epoch + 1; epoch++) {
    res = await request_api(
      provider_url + "/eth/v1/validator/duties/proposer/" + epoch
    );

    if ("data" in res) {
      slots = res["data"].reverse();

      $.each(slots, async function (index, slot) {
        slot["epoch"] = epoch;
        slot["slot_number"] = slot["slot"];

        slot["status"] = "Scheduled";
        slot["block"] = "-";
        slot["time"] = "";

        if (slot["slot_number"] <= current_slot) {
          block = await request_api(
            provider_url + "/eth/v2/beacon/blocks/" + slot["slot_number"]
          );
          if ("data" in block) {
            block_number =
              block.data.message.body.execution_payload.block_number;

            slot["timestamp"] =
              block.data.message.body.execution_payload.timestamp;
            slot["status"] = "Proposed";
            slot[
              "block"
            ] = `<a href='/block/${block_number}'>${block_number}</a>`;
            slot[
              "slot"
            ] = `<a href='/slot-details/${slot.slot}'>${slot.slot}</a>`;
            let sec = Math.floor((Date.now() - slot.timestamp * 1000) / 1000);
            slot[
              "time"
            ] = `<a hidden id=${slot.slot_number}_timestamp> ${slot.timestamp}</a>`;
            if (sec < 60) {
              slot["time"] += `${sec} seconds ago`;
            } else {
              let min = Math.floor(sec / 60);
              if (min == 1) {
                slot["time"] += `${Math.floor(sec / 60)} min ago`;
              } else {
                slot["time"] += `${Math.floor(sec / 60)} mins ago`;
              }
            }
          } else {
            slot["status"] = "Skipped";
          }
        }
      });

      committees = await request_api(
        provider_url + "/eth/v1/beacon/states/" + epoch * 4 + "/committees"
      );

      if ("data" in committees) {
        committees = committees["data"];
        $.each(committees, function (index, committee) {
          $.each(slots, async function (index, slot) {
            if (committee["slot"] == slot["slot_number"]) {
              if (!("committees" in slot)) {
                slot["committees"] = {};
              }
              slot["committees"][committee["index"]] = committee["validators"];
            }
          });
        });
      }
      slot_info = slots.concat(slot_info);
    }
  }

  current_epoch = updated_epoch;
  loadTable(
    "table-body",
    [
      "epoch",
      "slot",
      "block",
      "status",
      "time",
      "validator_index",
      "committees",
    ],
    slot_info
  );
}

async function update_slot() {
  let updated_slot = await get_current_slot();
  updated_epoch = Math.floor(parseInt(updated_slot) / 4);

  if (current_epoch < updated_epoch) {
    for (let epoch = current_epoch + 2; epoch <= updated_epoch + 1; epoch++) {
      res = await request_api(
        provider_url + "/eth/v1/validator/duties/proposer/" + epoch
      );

      if ("data" in res) {
        slots = res["data"];

        $.each(slots, async function (index, slot) {
          slot["epoch"] = epoch;
          slot["status"] = "Scheduled";
          slot["block"] = "-";
          slot["time"] = "";
          insertTable(
            "table-body",
            [
              "epoch",
              "slot",
              "block",
              "status",
              "time",
              "validator_index",
              "committees",
            ],
            slot
          );
        });
      }
    }

    for (let epoch = current_epoch + 1; epoch <= updated_epoch; epoch++) {
      if (epoch <= updated_epoch) {
        committees = await request_api(
          provider_url + "/eth/v1/beacon/states/" + epoch * 4 + "/committees"
        );
        if ("data" in committees) {
          committees = committees["data"];
          $.each(committees, function (index, committee) {
            let committeesCell = document.getElementById(
              committee.slot + "_committees"
            );
            let newText = document.createTextNode(
              "{" + committee["index"] + ":[" + committee["validators"] + "]}  "
            );
            committeesCell.appendChild(newText);
          });
        }
      }
    }
  }
  current_epoch = updated_epoch;
  update_status(updated_slot);
}

async function update_status(updated_slot) {
  if (current_slot < updated_slot) {
    for (let s = current_slot + 1; s <= updated_slot; s++) {
      block = await request_api(provider_url + "/eth/v2/beacon/blocks/" + s);
      if ("data" in block) {
        block_number = block.data.message.body.execution_payload.block_number;

        $("#" + s.toString() + "_status").html("Proposed");
        $("#" + s.toString() + "_block").html(
          `<a href='/block/${block_number}'>${block_number}</a>`
        );
        $("#" + s.toString() + "_slot").html(
          `<a href='/slot-details/${s}'>${s}</a>`
        );
        let timestamp = block.data.message.body.execution_payload.timestamp;
        let sec = Math.floor((Date.now() - timestamp * 1000) / 1000);
        let time = `<a hidden id=${s}_timestamp> ${timestamp}</a>`;

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
        $("#" + s.toString() + "_time").html(time);
      } else {
        $("#" + s.toString() + "_status").html("Skipped");
      }
    }
  }
  current_slot = updated_slot;
}

async function update_timestamp() {
  let initial_slot = initial_epoch * 4;
  for (let slot = initial_slot; slot <= current_slot; slot++) {
    let timecell = document.getElementById(`${slot}_timestamp`)
    if (timecell == null){
        continue
    }
    let timestamp = parseInt(
      timecell.innerText
    );
    let sec = Math.floor((Date.now() - timestamp * 1000) / 1000);
    let time = `<a hidden id=${slot}_timestamp> ${timestamp}</a>`;
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
    $("#" + slot.toString() + "_time").html(time);
  }
}
