window.onload = function(){

    init();
}

const addresses = []
const unit = 0.000000000000000001;

async function init(){

    // get all the current addresses from front-end
    let addresses_tag = document.getElementsByClassName("account-address");
    for(let x = 0; x < addresses_tag.length; x++){
        addresses.push(addresses_tag[x].innerHTML);
    }
    if (typeof window.ethereum !== "undefined" && ethereum.isMetaMask){
        var accounts = await ethereum.request({method: "eth_requestAccounts"});

        // check if current connected account in address list
        addr = ethers.utils.getAddress(accounts[0]);
        if(!addresses.includes(addr)){
            addresses.push(addr);
            create_account_record(addr);
            metamask_status_init();
        }
      }
    else{
        alert("Please install metamask in your browser!");
    }
}

async function metamask_status_init(){

    window.ethereum.on('accountsChanged', async function (new_accounts) {
      // check if current connected account in address list
      addr = ethers.utils.getAddress(new_accounts[0]);
      if(!addresses.includes(addr)){
        addresses.push(addr);
        create_account_record(addr);
      }
      console.log("check!");
    });
  
}

async function create_account_record(addr){
    let table_body = document.getElementById('table-body');
    let tr = document.createElement('tr');
    let address_td = document.createElement('td');
    let balance_td = document.createElement('td');
    let source_td = document.createElement('td');
    let diff_td = document.createElement('td');
    address_td.innerHTML = addr;
    address_td.className = "account-address";
    source_td.innerHTML = "MetaMask";
    balance_td.innerHTML = await get_balance(addr);
    diff_td.innerHTML = 0;
    tr.appendChild(address_td);
    tr.appendChild(source_td);
    tr.appendChild(balance_td);
    
    tr.appendChild(diff_td);
    table_body.prepend(tr);
}

async function get_balance(address){
    var res = await ethereum
    .request({
      method: 'eth_getBalance',
      params: [address, "latest"],
    });
    ether = parseInt(res, 16) * unit;
    return ether;
  }