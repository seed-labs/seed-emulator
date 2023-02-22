// Display the selected tab
function openTab(evt, tabName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " active";
}

async function set_navigator() {
  consensus = await get_consensus();
  if (consensus=='POS') {
      const nav = document.getElementById("side_nav");

      var validator_tab = document.createElement("a");
      validator_tab.href = "/validator-view"
      var validator_tab_textnode = document.createTextNode("Validators")
      validator_tab.appendChild(validator_tab_textnode)
      nav.appendChild(validator_tab)

      var slot_tab = document.createElement("a");
      slot_tab.href = "/slot-view"
      var slot_tab_textnode = document.createTextNode("Slots")
      slot_tab.appendChild(slot_tab_textnode)
      nav.appendChild(slot_tab)
  }
}

async function get_consensus() {
  var consensus = await request_api("/get_consensus");
  console.log(consensus)
  return consensus;
}

async function request_api(url) {
  const response = await fetch(url);
  
  res = response.json();
  
  if (response) {
      return res;
  } else {
      return null;
  }
  }
    