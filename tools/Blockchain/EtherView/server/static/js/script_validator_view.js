window.onload = function () {
    init();
};

async function init() {
    providers = await get_beacon_providers();
    if (providers!=null) {
        set_provider_selector();
    }
    await set_navigator();
    
    update_validator();
    update_current_slot();

    window.setInterval(update_validator, 5000);
    window.setInterval(update_current_slot, 5000)
}

async function update_validator(){
    const response = await fetch(provider_url+"/eth/v1/beacon/states/head/validators");
    
    validators = await response.json();

    let parsed_validators_info = [];
    $.each(validators['data'].reverse(), function(index, validator){
        parsed_validators_info.push({...validator, ...validator['validator']});
    });

    loadTable('table-body', ['index', 'balance', 'status', 'activation_eligibility_epoch', 'activation_epoch', 'pubkey'], parsed_validators_info)
}


