window.onload = function(){
  init();
}



const unit = 0.000000000000000001;
var uploaded = false;
var metamask_connected = false;
var accounts;
var iface;


function init(){
    document.getElementById("upload").onclick = function(){uploadAndDeploy("upload")};
    document.getElementById("deploy").onclick = function(){uploadAndDeploy("deploy")};
}

function isNumeric(value) {
  return /^-?\d+$/.test(value);
}

function verify_arguments(value, type){
  type = type.toLowerCase()
  if (type == "string"){
    return true;
  }
  else if (type == "address"){
    if (value.length == 42 && value.slice(0, 2) == "0x"){
      return true;
    }
    else{
      alert("Please input a correct address");
      return false;
    }
  }
  else if (value.includes("uint") && ! value.includes("[]")){
    if (isNumeric(value)){
      return true;
    }
    else{
      alert("You must input integer variable!");
      return false;
    }
  }
  else{
    alert("Only support String, address and uint types of arguments!");
    return false;
  }


}

function uploadAndDeploy(evt){
    const abi_file = document.getElementById("abi-file").files[0];
    const bin_file = document.getElementById("bin-file").files[0];
    if (!metamask_connected){
      alert("Please connect MetaMask first!");
      return;
    }

    if (abi_file && bin_file) {
        var abi_name= abi_file['name'].split('.');
        var bin_name= bin_file['name'].split('.');
        if (abi_name[0] !== bin_name[0]){
            alert('file names are not matched!')
            return
        }
        if (evt == "upload"){
            uploaded = true;
            alert('files have been uploaded!')
            displayABI(abi_file);
        }
        else if (evt == "deploy" && uploaded){

            
            var value_unit = document.getElementById("value-unit");
            value_unit = value_unit.options[value_unit.selectedIndex].text;

            let gas_limit = parseInt(document.getElementById("gas-limit").value);
            let wei_value = parseInt(document.getElementById("ether-value").value);
            if ( wei_value > 0 && !payable_constructor ){
                alert('Contract must contain a payable constructor for depositing ether value during deploying!. Otherwise, set it to 0');
                return;
            }

            let arguments = document.querySelectorAll('[id^="argument"]');
            
            var parameters_for_constructor = []
            for(let i = 0; i < arguments.length; i++){
                if(!arguments[i].checkValidity()){
                    alert("Argument(s) cannot be empty and must be valid!");

                    return;
                }
                else if (!verify_arguments(arguments[i].value, arguments[i].placeholder)){
                  return;
                }
                if (arguments[i].placeholder.includes("uint")){
                  parameters_for_constructor.push(parseInt(arguments[i].value));
                }
                else{
                  parameters_for_constructor.push(arguments[i].value);
                }
            }

            var encode_arguments = iface.encodeDeploy(parameters_for_constructor)
            
            if (value_unit == "Ether"){
                wei_value *= 1000000000000000000;
            }
            else if (value_unit == "Gwei"){
                wei_value *= 1000000000;
            }
            var reader = new FileReader();
            var reader1 = new FileReader();
            var abi;
            var bin;
            reader.readAsText(bin_file, "UTF-8");
            
            var deploy_btn = document.getElementById("deploy");
            deploy_btn.style.display = "none";

            reader.onload = function (evt) {
                bin = evt.target.result;
                bin = bin.trim();
                reader1.readAsText(abi_file, "UTF-8");
                
            }
            reader1.onload = function(evt){
                abi = evt.target.result;
                var data = {"abi": abi, "bin":bin + encode_arguments.slice(2), "name": abi_name[0], "gas_limit": gas_limit, "wei-value": wei_value};
                deploy_via_metamask(data);
            }
            uploaded = false;
            contained_constructor = false;
            payable_constructor = false;
        }
        else{
            alert('You need to upload both .abi and .bin files first!');
        }
    }
    else{

        alert('You need to upload both .abi and .bin files!');
    }

}


function displayABI(abi_file){
    var reader = new FileReader();
    reader.readAsText(abi_file, "UTF-8");
    reader.onload = function (evt) {
      // load abi file by ethers.js
        json_abi = JSON.parse(evt.target.result);
        iface = new ethers.utils.Interface(json_abi);
        const FormatTypes = ethers.utils.FormatTypes;
        const readable_abi = iface.format(FormatTypes.minimal);
        let abi_pre_block = document.getElementById("abi-pre-block");
        abi_pre_block.innerHTML="";      // clear all abi functions shown before

        
        // append abi function string to front-end
        for(let i = 0; i < readable_abi.length; i++){
            var function_span_tag = document.createElement('span');
            function_span_tag.innerHTML = readable_abi[i];
            function_span_tag.style.display= "block";
            abi_pre_block.appendChild(function_span_tag);
        }

        // clear all arguments input from last uploaded contract
        var arugments_block = document.getElementsByClassName("deploy-arugments-block")[0];
        arugments_block.style.display = "none";
        arugments_block.innerHTML = "";

        // add arguments input from current uploaded contract for deployment
        for (let i = 0; i < json_abi.length; i++){
            let method = json_abi[i];
            if (method['type'] == "constructor"){
                contained_constructor = true;
                if(method['inputs'] != "undefined"){
                    var inputs = method['inputs'];
                    for(let j = 0; j < inputs.length; j++){
                        let arg_name_tag = document.createElement('label');
                        let arg_input_tag = document.createElement('input');
                        arg_input_tag.id = "argument" + j;
                        arg_input_tag.required = true;
                        arg_name_tag.innerHTML = inputs[j]['name'] + ": ";
                        arg_input_tag.type = "text";
                        arg_input_tag.placeholder = inputs[j]['type'];
                        arg_name_tag.appendChild(arg_input_tag);
                        arugments_block.appendChild(arg_name_tag);
                    }
                    arugments_block.style.display = "flex";
                }
                
                if (method['stateMutability'] == "payable"){
                    payable_constructor = true;
                }
            }
        }
            
    }
    reader.onerror = function (evt) {
        document.getElementById("abi-pre-block").innerHTML = "error reading file";
    }
 
}



function printingDeployStatus(response, error){
  var deploy_btn = document.getElementById("deploy");
  deploy_btn.style.display = "initial";
  let msg = document.createElement('span');
  let deploy_status_block = document.getElementById("deploy-status-block");
  if (error){
      msg.innerHTML = "-> " + response;
      msg.style.color = "red";
  }
  else if(response == 200){
      msg.innerHTML = "-> Contract deployed successfully!";
      msg.style.color = "green";
  }
  else{

      msg.innerHTML = "-> " + response
      msg.style.color = "red";
  }
  
  msg.classList.add('new-msg');
  deploy_status_block.append(msg);
  deploy_status_block.scrollTop = deploy_status_block.scrollHeight;
}



// deploy a contract 
async function deploy_via_metamask(information){

  const transactionParameters = {
    nonce: '0x00', // ignored by MetaMask
    gasPrice: '0xBA43B7400', // customizable by user during MetaMask confirmation.
    gas: '0x' + information['gas_limit'].toString(16), // customizable by user during MetaMask confirmation.
    to: null, // Required except during contract publications.
    from: ethereum.selectedAddress, // must match user's active address.
    value: '0x' + information['wei-value'].toString(16), // Only required to send ether to the recipient from the initiating external account.
    data: information['bin'], // Optional, but used for defining smart contract creation and interaction.
    chainId: ethereum.networkVersion, // Used to prevent transaction reuse across blockchains. Auto-filled by MetaMask.
  };

  await ethereum.request({
    method: 'eth_sendTransaction',
    params: [transactionParameters],
  }).then(async (txHash)=> {
    // get receipt by txhash
    const receipt = await get_receipt_by_hash(txHash);

    information['block_number'] = receipt.blockNumber;
    information['contract_address'] = receipt.contractAddress;
    let address_head = receipt.from.slice(0,5);
    let address_end = receipt.from.slice(-6,-1);
    information['owner'] = address_head + "..." + address_end;
    information['balance'] = await get_balance(receipt.contractAddress);

    // add the contract data to database
    add_contract_data(information);
  }).catch((error) => {
    error_msg = error.message.split(':')
    printingDeployStatus(error_msg[1], true);
  });



  
}

async function add_contract_data(information){
    $.ajax({
    type: "POST",
    url: "/contract/api/add-contract-data",
    data: JSON.stringify(information),
    dataType: 'json',
    contentType: "application/json",
    processData: false,
    success: function(response) {
      printingDeployStatus(200, false);
    }
    });
}

async function get_receipt_by_hash(txHash){
  let account_option = document.getElementById("account_option");
  
  let account_ether = await get_balance(accounts[0]);
  address_head = accounts[0].slice(0,5);
  address_end = accounts[0].slice(-6,-1);
  account_option.innerHTML = address_head + "..." + address_end + " ("+account_ether+ " ether) ";
  
  // using ethers.js to get the transaction which will wait for the block is mined.
  var provider = ethers.getDefaultProvider("http://10.150.0.71:8545");
  var receipt = await provider.waitForTransaction(txHash);

  return receipt;

}

async function connect_metamask(){
  if (typeof window.ethereum !== "undefined" && ethereum.isMetaMask){
    // get current connected account
    metamask_connected = true;
    accounts = await ethereum.request({method: "eth_requestAccounts"});
    // accounts[0] is storing current account address
    let account_option = document.getElementById("account_option");
    let account_ether = await get_balance(accounts[0]);
    let address_head = accounts[0].slice(0,5);
    let address_end = accounts[0].slice(-6,-1);
    account_option.innerHTML = address_head + "..." + address_end + " ("+account_ether+ " ether) ";

    // init action if connected account changed
    metamask_status_init();

    let connected_btn = document.getElementById("connected_btn");
    let conntect_cross = document.getElementById("connect_cross");
    let conntect_tick = document.getElementById("connect_tick");
    connected_btn.style.display = "none";
    conntect_cross.style.display = "none";
    conntect_tick.style.display = "flex";
  }
  else{
    alert("Please install metamask in your browser!");
  }
}

// get the balance of address
async function get_balance(address){
  var res = await ethereum
  .request({
    method: 'eth_getBalance',
    params: [address, "latest"],
  });
  ether = parseInt(res, 16) * unit;
  return ether;
}

async function metamask_status_init(){

  window.ethereum.on('accountsChanged', async function (new_accounts) {
    accounts[0] = new_accounts[0]
    let account_option = document.getElementById("account_option");

    // if we can't get an account, user have to connect an account
    if (new_accounts.length == 0){
      account_option.innerHTML = "";
      let connected_btn = document.getElementById("connected_btn");
      let conntect_cross = document.getElementById("connect_cross");
      let conntect_tick = document.getElementById("connect_tick");
      connected_btn.style.display = "initial";
      conntect_cross.style.display = "block";
      conntect_tick.style.display = "none";
      metamask_connected = false;
    }
    // change page information for current connected account
    else{ 
      let account_ether = await get_balance(new_accounts[0]);
      address_head = new_accounts[0].slice(0,5);
      address_end = new_accounts[0].slice(-6,-1);
      account_option.innerHTML = address_head + "..." + address_end + " ("+account_ether+ " ether) ";
    }
  });

}





