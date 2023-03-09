window.onload = function(){
    init();
}

var contract;
var address;
var abi;

function init(){

    // Using ethers.js to connect to emulator network
    var provider = ethers.getDefaultProvider("http://10.150.0.71:8545");
    address = document.getElementById("contract-address").innerHTML;
    address = address.trim()

    // request server to get abi by address
    $.ajax({
        type: "GET",
        url:"/contract/api/get_abi_by_address/"+address,
        data: "",
        dataType: 'json',
        contentType: "application/json",
        precessData: false,
        success: async function(response){
            abi = response.abi;
            contract = new ethers.Contract(address, response.abi, provider);
        },
        error: function(error){
            console.log(error);
        }
    });
    
}

async function get_alice_balance(){
    var alice_balance = await contract.getAliceBalance();
    var output_area = document.getElementById("contract-call-output");
    output_area.innerHTML = alice_balance;
}

async function get_bob_balance(){
    var bob_balance = await contract.getBobBalance();
    var output_area = document.getElementById("contract-call-output");
    output_area.innerHTML = bob_balance;
}

async function deposit(){
    var value = parseInt(document.getElementById("value-box").value);
    value *= 1000000000000000000;
    var iface = new ethers.utils.Interface(abi)
    bin = iface.encodeFunctionData("deposit");

    const transactionParameters = {
        nonce: '0x00', // ignored by MetaMask
        gasPrice: '0xBA43B7400', // customizable by user during MetaMask confirmation.
        gas: '0x1E8480', // customizable by user during MetaMask confirmation.
        to: address, // Required except during contract publications.
        from: ethereum.selectedAddress, // must match user's active address.
        value: '0x' + value.toString(16), // Only required to send ether to the recipient from the initiating external account.
        data: bin, // Optional, but used for defining smart contract creation and interaction.
        chainId: ethereum.networkVersion, // Used to prevent transaction reuse across blockchains. Auto-filled by MetaMask.
    };
    
    await ethereum.request({
    method: 'eth_sendTransaction',
    params: [transactionParameters],
    }).then(async (txHash)=> {
        console.log(txHash);
    }).catch((error) => {
        console.log(error);
    });

}


async function withdraw(){

    var value = parseInt(document.getElementById("value-box").value);
    var iface = new ethers.utils.Interface(abi)
    bin = iface.encodeFunctionData("withdraw",[value]);

    const transactionParameters = {
        nonce: '0x00', // ignored by MetaMask
        gasPrice: '0xBA43B7400', // customizable by user during MetaMask confirmation.
        gas: '0x1E8480', // customizable by user during MetaMask confirmation.
        to: address, // Required except during contract publications.
        from: ethereum.selectedAddress, // must match user's active address.
        value: '0x00', // Only required to send ether to the recipient from the initiating external account.
        data: bin, // Optional, but used for defining smart contract creation and interaction.
        chainId: ethereum.networkVersion, // Used to prevent transaction reuse across blockchains. Auto-filled by MetaMask.
    };
    
    await ethereum.request({
    method: 'eth_sendTransaction',
    params: [transactionParameters],
    }).then(async (txHash)=> {
        console.log(txHash);
    }).catch((error) => {
        console.log(error);
    });

}