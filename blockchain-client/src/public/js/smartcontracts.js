let url;
const deployedContracts = []

function displayDeployedContractFunctions(func) {
	if(func.name) {
		const numOfParameters = func.inputs.length;
		const functionButton = document.createElement('input')
		functionButton.type = "button"
		functionButton.value = func.name;
		functionButton.setAttribute('data-action', 'invokeContractFunction')
		functionButton.setAttribute('data-abi', deployedContracts.length - 1)

		const parentContainer = document.querySelector(`.deployedContractContainer[data-abi="${deployedContracts.length-1}"]`);
		parentContainer.appendChild(functionButton)
		func.inputs.forEach((input) => {
			const paramInput = document.createElement('input')
			paramInput.placeholder = input.name
			paramInput.className = func.name + "-param"
			paramInput.setAttribute('data-type', input.type)
			parentContainer.appendChild(paramInput)
		})
		
		functionButton.addEventListener('click', (event) =>{
			const params = document.getElementsByClassName(func.name+"-param")
			const paramValues = []
			Array.from(params).forEach((param) => {paramValues.push({value: param.value, type: param.dataset.type})})
			paramValues.unshift(deployedContracts[event.target.dataset.abi])
			xmlHttpRequestHandler('POST', url, {
				action: event.target.dataset.action,
				params: [event.target.value,window.selectedAccount ,paramValues],
				containerId: window.containerId
			}, responseHandler)
		})
	}
}

function xmlHttpRequestHandler(type, url, data={}, callback) {
	const http = new XMLHttpRequest();
	http.open(type, url, true);
	http.onreadystatechange = function() {
		if(http.readyState === XMLHttpRequest.DONE) {
			callback(JSON.parse(http.responseText))
		}
	}
	http.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
	http.send(JSON.stringify(data));
}


function responseHandler({action, response}) {
	if(action === 'deploySmartContract') {
		document.getElementById('displayTransactionOutput').innerHTML = response
	} else if(action === 'getTransactionReceipt') { 
		document.getElementById('displayTransactionReceipt').innerHTML = response
	} else if (action ==="getContractByAddress") {
		const abi = document.getElementById("abi").value
		const address = document.getElementById("smartContractAddress").value
		deployedContracts.push({abi, address})
		const contractContainer = document.createElement('div')
		contractContainer.className = 'deployedContractContainer'
		contractContainer.setAttribute('data-abi', deployedContracts.length - 1)
		document.getElementById('displayContract').appendChild(contractContainer)
		JSON.parse(abi).forEach((f) => {
			displayDeployedContractFunctions(f);
		})
	}
}

window.addEventListener('DOMContentLoaded', ()=> {

	url = `http://localhost:${window.blockchainPort}/smartcontracts`

	const accounts = document.getElementById('accounts');
	window.selectedAccount = accounts.options[accounts.selectedIndex].value; 
	accounts.addEventListener('change', (event)=> {
  		window.selectedAccount = event.target.options[event.target.selectedIndex].value
	})
	
	const abiTextArea = document.getElementById('abi');
	const bytecodeTextArea = document.getElementById('bytecode');
	const parametersInput = document.getElementById('contract-params');
	const deployButton = document.getElementById('deploy')

	deployButton.addEventListener('click', (event) => {
		const abi = abiTextArea.value;
		const bytecode = bytecodeTextArea.value.substring(0,2) !== '0x' ? '0x' + bytecodeTextArea.value : bytecodeTextArea.value;	
		const params = parametersInput.value;

		if(!abi || !bytecode) {
			alert("Abi and Bytecode are mandatory")
			return
		}

		xmlHttpRequestHandler('POST', url, {
			params: [window.selectedAccount, abi, bytecode, params],
			action: event.target.dataset.action,
			containerId: window.containerId
		}, responseHandler)

	})

	const getTransactionReceiptButton = document.getElementById("getTransactionReceipt");
	const transactionHashInput = document.getElementById("transactionHash")

	getTransactionReceiptButton.addEventListener('click', (event)=>{
		xmlHttpRequestHandler('POST', url, {
			action: event.target.dataset.action,
			params: [transactionHashInput.value],
			containerId: window.containerId
		}, responseHandler)
	})

	const getContractButton = document.getElementById("getSmartContract");
	const contractAddressInput = document.getElementById("smartContractAddress");

	getContractButton.addEventListener('click', (event)=> {
		xmlHttpRequestHandler('POST', url, {
			action: event.target.dataset.action,
			params: [abiTextArea.value, contractAddressInput.value],
			containerId: window.containerId
		}, responseHandler)
	})

})
