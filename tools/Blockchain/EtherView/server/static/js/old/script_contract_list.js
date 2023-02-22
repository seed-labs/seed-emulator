window.onload = function(){
    init();
}

function init(){
    auto_refresh_table();
    pop_up_window_cross_btn()
}

var able_refresh = true;

function abi_pop_up(json_abi, contract_name){
    const iface = new ethers.utils.Interface(json_abi);
    const FormatTypes = ethers.utils.FormatTypes;
    const readable_abi = iface.format(FormatTypes.minimal);
    let abi_window_content = document.getElementById("abi-window-content");
    for(let i = 0; i < readable_abi.length; i++){
        var function_span_tag = document.createElement('span');
        function_span_tag.innerHTML = readable_abi[i];
        function_span_tag.style.display= "block";
        abi_window_content.appendChild(function_span_tag);
    }
    document.querySelector(".contract_name").innerHTML = contract_name;
    document.querySelector(".popup").style.display = "block";
            
}

function delete_smart_contract(address){
    $.ajax({
        type: "DELETE",
        url:"/contract/api/delete-contract/"+address,
        data: "",
        dataType: 'json',
        contentType: "application/json",
        precessData: false,
        success: function(response){
            console.log(response);
        },
        error: function(error){
            console.log(error);
        }
    });
}

function close_abi_window(){
    document.querySelector("#abi-window-content").innerHTML = "";
    document.querySelector(".popup").style.display = "none";
}

function delete_btn(address, contract_name){
    able_refresh = false;
    if (window.confirm("Are you sure to delete smart contract " + contract_name + "?")){
        contract_tag = document.getElementById(address);
        contract_tag.parentNode.removeChild(contract_tag);
        delete_smart_contract(address);  
    }
    able_refresh = true;
}

function auto_refresh_table(){
    const table_body = document.getElementById("table_body");

    setInterval(function(){
        fetch("/contract-list-table",{
            method: "GET"
        })
        .then(response =>{
            return response.text();
        })
        .then(html =>{
            if(able_refresh){
                table_body.innerHTML = html;
            }
        });
     }, 8000);
     
}


function pop_up_window_cross_btn(){
    document.querySelector(".btn-close").onclick = function(){close_abi_window()};
}