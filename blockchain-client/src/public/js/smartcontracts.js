let url;
const deployedContracts = []

function getSanitizedAbiValue(abi) {
	return JSON.stringify(JSON.parse(abi)
		.map((f)=>{
			if(f.stateMutability === 'payable') {
				f.payable=true
			}
			return f;
		}))
}

function displayDeployedContractFunctions(func) {
	if(func.name) {
		const numOfParameters = func.inputs.length;
		const functionButton = document.createElement('input')
		functionButton.type = "button"
		functionButton.value = func.name;
		functionButton.setAttribute('data-action', 'invokeContractFunction')
		functionButton.setAttribute('data-abi', deployedContracts.length - 1)

		if(func.payable) {
			functionButton.setAttribute('data-payable', true)
		}

		const parentContainer = document.querySelector(`.deployedContractContainer[data-abi="${deployedContracts.length-1}"]`);
		parentContainer.appendChild(functionButton)

		func.inputs.forEach((input) => {
			const paramInput = document.createElement('input')
			paramInput.placeholder = input.name
			paramInput.className = func.name + "-param"
			paramInput.setAttribute('data-type', input.type)
			parentContainer.appendChild(paramInput)
		})

		const outputContainer = document.createElement('div')
		outputContainer.className= func.name + "-output"
		outputContainer.setAttribute('data-abi', deployedContracts.length - 1)
		parentContainer.appendChild(outputContainer);
		
		functionButton.addEventListener('click', (event) =>{
			const params = document.getElementsByClassName(func.name+"-param")
			const functionInfo = {
				funcName: event.target.value,
				abiIndex: event.target.dataset.abi,
				payable: event.target.dataset.payable
			}
			const functionParameters = Array.from(params).map((param) => {
					return {
						value: param.value, 
						type: param.dataset.type
					}
				})
			const {abi, address} = deployedContracts[event.target.dataset.abi]
			const valueEl = document.querySelector('#paymentSection input')
			const value = valueEl.value || undefined
			const additionalData = [
				window.selectedAccount, 
				{abi: getSanitizedAbiValue(abi), address}, 
				document.querySelector('#paymentSection input').value || undefined
			]
			xmlHttpRequestHandler('POST', url, {
				action: event.target.dataset.action,
				params: [functionInfo, functionParameters, additionalData],
				containerId: window.containerId
			}, responseHandler)

			valueEl.value = ''
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
	if(responseHandler[action]) {
		responseHandler[action](response);
	}
}

responseHandler.deploySmartContract = function(response) {
	document.getElementById('displayTransactionOutput').innerHTML = response
}

responseHandler.getTransactionReceipt = function(response) {
	document.getElementById('displayTransactionReceipt').innerHTML = response
}

responseHandler.getContractByAddress = function(response) {
	const abi = getSanitizedAbiValue(document.getElementById("abi").value)
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

responseHandler.invokeContractFunction = function(response) {
	console.log('Invoked smart contract function: ', response);
	const {output, funcName, abiIndex} = JSON.parse(response);
	const el = document.querySelector(`.${funcName}-output[data-abi="${abiIndex}"]`)
	if(el) {
		el.innerHTML = output
	}
	
}

async function copyToClipboard(text) {
	/*const dummy = document.createElement("textarea");
    	document.body.appendChild(dummy);
    	dummy.value = text;
    	dummy.select();
    	document.execCommand("copy");
    	document.body.removeChild(dummy);
	*/
	return await navigator.clipboard.writeText(text)
}

window.addEventListener('DOMContentLoaded', ()=> {

	url = `http://localhost:${window.blockchainPort}/smartcontracts`

	const accounts = document.getElementById('accounts');
	window.selectedAccount = accounts.options[accounts.selectedIndex].value; 
	accounts.addEventListener('change', (event)=> {
  		window.selectedAccount = event.target.options[event.target.selectedIndex].value
	})

	const copy = document.getElementById("copySelectedAccount")
	
	copy.addEventListener('click', ()=> {
		copyToClipboard(window.selectedAccount)	
	})
	
	const abiTextArea = document.getElementById('abi');
	const bytecodeTextArea = document.getElementById('bytecode');
	const parametersInput = document.getElementById('contract-params');
	const deployButton = document.getElementById('deploy')

	const valueEl = document.querySelector('#paymentSection input')

	deployButton.addEventListener('click', (event) => {
		const abi = getSanitizedAbiValue(abiTextArea.value);
		window.deployedAbi = abi
		const bytecode = bytecodeTextArea.value.substring(0,2) !== '0x' ? '0x' + bytecodeTextArea.value : bytecodeTextArea.value;	
		const params = parametersInput.value.split(",").map(p => JSON.stringify(p)).join(",");
		const value = valueEl.value || undefined;
			
		if(!abi || !bytecode) {
			alert("Abi and Bytecode are mandatory")
			return
		}
		
		xmlHttpRequestHandler('POST', url, {
			params: [window.selectedAccount, abi, bytecode, params, value],
			action: event.target.dataset.action,
			containerId: window.containerId
		}, responseHandler)

		//bytecodeTextArea.value = ''
		//parametersInput.value = ''
		valueEl.value = ''
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
			params: [getSanitizedAbiValue(abiTextArea.value), contractAddressInput.value],
			containerId: window.containerId
		}, responseHandler)
	})

})
