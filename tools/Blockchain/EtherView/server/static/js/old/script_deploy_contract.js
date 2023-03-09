
window.onload = function(){
    init();
}

function init(){
    document.getElementById("upload").onclick = function(){uploadAndDeploy("upload")};
    document.getElementById("deploy").onclick = function(){uploadAndDeploy("deploy")};


}

var uploaded = false;
var contained_constructor = false;
var payable_constructor = false;

function uploadAndDeploy(evt){
    const abi_file = document.getElementById("abi-file").files[0];
    const bin_file = document.getElementById("bin-file").files[0];
    

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
            var wallet_account = document.getElementById("account");
            var value_unit = document.getElementById("value-unit");
            value_unit = value_unit.options[value_unit.selectedIndex].text;
            wallet_account = wallet_account.options[wallet_account.selectedIndex].text;
            wallet_account = wallet_account.split(":");
            let gas_limit = parseInt(document.getElementById("gas-limit").value);
            let ether_value = parseInt(document.getElementById("ether-value").value);
            if ( ether_value > 0 && !payable_constructor ){
                alert('Contract must contain a payable constructor for depositing ether value during deploying!. Otherwise, set it to 0');
                return;
            }

            let arguments = document.querySelectorAll('[id^="argument"]');
            
            for(let i = 0; i < arguments.length; i++){
                if(!arguments[i].checkValidity()){
                    alert("Argument(s) cannot be empty!");
                    return;
                }
            }
            
            // The following if-statement will be delete after supported.
            if (arguments.length > 0){
                alert("not suppot contract with arguments deployment!");
                return;
            }
            
            
            if (value_unit == "Wei"){
                ether_value *= 0.000000000000000001;
            }
            else if (value_unit == "Gwei"){
                ether_value *= 0.000000001;
            }
            var reader = new FileReader();
            var reader1 = new FileReader();
            var abi;
            var bin;
            reader.readAsText(bin_file, "UTF-8");
            
            reader.onload = function (evt) {
                bin = evt.target.result;
                reader1.readAsText(abi_file, "UTF-8");
                
            }
            reader1.onload = function(evt){
                abi = evt.target.result;
                var data = {"abi": abi, "bin":bin, "wallet_name":wallet_account[0], "account": wallet_account[1], "name": abi_name[0], "gas_limit": gas_limit, "ether-value": ether_value};
                deployment(data);
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
        json_abi = JSON.parse(evt.target.result);
        const iface = new ethers.utils.Interface(json_abi);
        const FormatTypes = ethers.utils.FormatTypes;
        const readable_abi = iface.format(FormatTypes.minimal);
        let abi_pre_block = document.getElementById("abi-pre-block");
        abi_pre_block.innerHTML="";      // clear all abi functions shown before

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
                        arg_input_tag.id = "argument" + i;
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
    let msg = document.createElement('span');
    let deploy_status_block = document.getElementById("deploy-status-block");
    if (error){
        msg.innerHTML = "-> " + response.statusText;
        msg.style.color = "red";
    }
    else if(response.code == 200){
        msg.innerHTML = "-> Contract deployed successfully!";
        msg.style.color = "green";
    }
    else{

        msg.innerHTML = "-> " + response.message;
        msg.style.color = "red";
    }
    
    msg.classList.add('new-msg');
    deploy_status_block.append(msg);
    deploy_status_block.scrollTop = deploy_status_block.scrollHeight;
}


function deployment(information){
    $.ajax({
        type: "POST",
        url: "/contract-deploy",
        data: JSON.stringify(information),
        dataType: 'json',
        contentType: "application/json",
        processData: false,
        success: function(response) {
            printingDeployStatus(response, false);
        },
        error: function(error) {
            printingDeployStatus(error, true);
        }
    });
    

}

